// Managed by Ansible (ai_workstation role)
// Local HTTP reverse proxy for dragtokens.com that connects upstream via TLS 1.3
// Encrypted Client Hello (ECH), fetching the ECHConfigList from the local DoH
// resolver (127.0.0.1:53) TYPE65 (HTTPS) record.
package main

import (
	"context"
	"crypto/tls"
	"encoding/binary"
	"errors"
	"flag"
	"fmt"
	"log"
	"net"
	"net/http"
	"net/http/httputil"
	"net/url"
	"strings"
	"sync"
	"time"
)

type echState struct {
	mu        sync.RWMutex
	echConfig []byte
	ipv4Hints []string
	expiresAt time.Time
}

func buildHTTPSQuery(domain string) ([]byte, error) {
	labels := strings.Split(strings.TrimSuffix(domain, "."), ".")
	buf := make([]byte, 12, 64)
	binary.BigEndian.PutUint16(buf[0:2], 0x4543) // ID
	binary.BigEndian.PutUint16(buf[2:4], 0x0100) // RD=1
	binary.BigEndian.PutUint16(buf[4:6], 1)      // QDCOUNT=1
	for _, label := range labels {
		if len(label) == 0 || len(label) > 63 {
			return nil, fmt.Errorf("invalid dns label %q", label)
		}
		buf = append(buf, byte(len(label)))
		buf = append(buf, label...)
	}
	buf = append(buf, 0x00)                  // root
	buf = binary.BigEndian.AppendUint16(buf, 65) // QTYPE = HTTPS (65)
	buf = binary.BigEndian.AppendUint16(buf, 1)  // QCLASS = IN (1)
	return buf, nil
}

func skipDNSName(msg []byte, offset int) (int, error) {
	for {
		if offset >= len(msg) {
			return 0, errors.New("truncated dns name")
		}
		b := msg[offset]
		if b == 0 {
			return offset + 1, nil
		}
		if b&0xC0 == 0xC0 {
			if offset+1 >= len(msg) {
				return 0, errors.New("truncated dns pointer")
			}
			return offset + 2, nil
		}
		offset += 1 + int(b)
	}
}

func queryHTTPSRecord(ctx context.Context, dnsAddr, domain string) ([]byte, []string, time.Duration, error) {
	query, err := buildHTTPSQuery(domain)
	if err != nil {
		return nil, nil, 0, err
	}
	var d net.Dialer
	conn, err := d.DialContext(ctx, "udp", dnsAddr)
	if err != nil {
		return nil, nil, 0, err
	}
	defer conn.Close()
	if dl, ok := ctx.Deadline(); ok {
		_ = conn.SetDeadline(dl)
	} else {
		_ = conn.SetDeadline(time.Now().Add(4 * time.Second))
	}
	if _, err := conn.Write(query); err != nil {
		return nil, nil, 0, err
	}
	resp := make([]byte, 4096)
	n, err := conn.Read(resp)
	if err != nil {
		return nil, nil, 0, err
	}
	msg := resp[:n]
	if len(msg) < 12 {
		return nil, nil, 0, errors.New("dns response too short")
	}
	qdCount := int(binary.BigEndian.Uint16(msg[4:6]))
	anCount := int(binary.BigEndian.Uint16(msg[6:8]))
	offset := 12
	for i := 0; i < qdCount; i++ {
		offset, err = skipDNSName(msg, offset)
		if err != nil || offset+4 > len(msg) {
			return nil, nil, 0, errors.New("invalid dns question section")
		}
		offset += 4
	}
	for i := 0; i < anCount; i++ {
		offset, err = skipDNSName(msg, offset)
		if err != nil || offset+10 > len(msg) {
			return nil, nil, 0, errors.New("invalid dns answer header")
		}
		rrType := binary.BigEndian.Uint16(msg[offset : offset+2])
		ttl := binary.BigEndian.Uint32(msg[offset+4 : offset+8])
		rdLen := int(binary.BigEndian.Uint16(msg[offset+8 : offset+10]))
		offset += 10
		if offset+rdLen > len(msg) {
			return nil, nil, 0, errors.New("truncated dns rdata")
		}
		rdata := msg[offset : offset+rdLen]
		offset += rdLen
		if rrType != 65 || len(rdata) < 2 {
			continue
		}
		svcPriority := binary.BigEndian.Uint16(rdata[0:2])
		if svcPriority == 0 {
			continue // AliasMode
		}
		pOff, err := skipDNSName(rdata, 2)
		if err != nil {
			continue
		}
		var ech []byte
		var ipv4s []string
		for pOff+4 <= len(rdata) {
			key := binary.BigEndian.Uint16(rdata[pOff : pOff+2])
			valLen := int(binary.BigEndian.Uint16(rdata[pOff+2 : pOff+4]))
			pOff += 4
			if pOff+valLen > len(rdata) {
				break
			}
			val := rdata[pOff : pOff+valLen]
			pOff += valLen
			switch key {
			case 4: // ipv4hint
				for j := 0; j+4 <= len(val); j += 4 {
					ipv4s = append(ipv4s, net.IP(val[j:j+4]).String())
				}
			case 5: // ech
				ech = append([]byte(nil), val...)
			}
		}
		if len(ech) > 0 {
			dur := time.Duration(ttl) * time.Second
			if dur < 60*time.Second {
				dur = 60 * time.Second
			}
			if dur > 30*time.Minute {
				dur = 30 * time.Minute
			}
			return ech, ipv4s, dur, nil
		}
	}
	return nil, nil, 0, fmt.Errorf("no HTTPS ECH record found for %s", domain)
}

func (s *echState) get(ctx context.Context, dnsAddr, domain string, forceRefresh bool) ([]byte, []string, error) {
	if !forceRefresh {
		s.mu.RLock()
		if len(s.echConfig) > 0 && time.Now().Before(s.expiresAt) {
			ech := s.echConfig
			ips := s.ipv4Hints
			s.mu.RUnlock()
			return ech, ips, nil
		}
		s.mu.RUnlock()
	}

	s.mu.Lock()
	defer s.mu.Unlock()
	if !forceRefresh && len(s.echConfig) > 0 && time.Now().Before(s.expiresAt) {
		return s.echConfig, s.ipv4Hints, nil
	}
	ech, ips, ttl, err := queryHTTPSRecord(ctx, dnsAddr, domain)
	if err != nil {
		if len(s.echConfig) > 0 {
			return s.echConfig, s.ipv4Hints, nil
		}
		return nil, nil, err
	}
	s.echConfig = ech
	s.ipv4Hints = ips
	s.expiresAt = time.Now().Add(ttl)
	return ech, ips, nil
}

func (s *echState) updateWithRetryConfig(retry []byte) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.echConfig = append([]byte(nil), retry...)
	s.expiresAt = time.Now().Add(15 * time.Minute)
}

func main() {
	listenAddr := flag.String("listen", "127.0.0.1:4097", "Local listen address")
	targetHost := flag.String("target", "dragtokens.com", "Upstream HTTPS hostname")
	dnsAddr := flag.String("dns", "127.0.0.1:53", "DNS resolver for HTTPS (TYPE65) ECH record")
	flag.Parse()

	state := &echState{}
	targetURL := &url.URL{
		Scheme: "https",
		Host:   *targetHost,
	}

	dialTLSContext := func(ctx context.Context, network, addr string) (net.Conn, error) {
		ech, ips, err := state.get(ctx, *dnsAddr, *targetHost, false)
		if err != nil {
			ech, ips, err = state.get(ctx, *dnsAddr, *targetHost, true)
			if err != nil {
				return nil, fmt.Errorf("fetch ECH config: %w", err)
			}
		}

		dialHost := *targetHost
		if len(ips) > 0 {
			dialHost = ips[0]
		}
		dialTarget := net.JoinHostPort(dialHost, "443")

		dialOnce := func(echBytes []byte) (net.Conn, error) {
			var d net.Dialer
			d.Timeout = 10 * time.Second
			rawConn, err := d.DialContext(ctx, "tcp4", dialTarget)
			if err != nil {
				return nil, err
			}
			tlsCfg := &tls.Config{
				ServerName:                     *targetHost,
				MinVersion:                     tls.VersionTLS13,
				EncryptedClientHelloConfigList: echBytes,
				NextProtos:                     []string{"h2", "http/1.1"},
			}
			tlsConn := tls.Client(rawConn, tlsCfg)
			if err := tlsConn.HandshakeContext(ctx); err != nil {
				_ = rawConn.Close()
				return nil, err
			}
			return tlsConn, nil
		}

		conn, err := dialOnce(ech)
		if err != nil {
			var echRej *tls.ECHRejectionError
			if errors.As(err, &echRej) && len(echRej.RetryConfigList) > 0 {
				state.updateWithRetryConfig(echRej.RetryConfigList)
				return dialOnce(echRej.RetryConfigList)
			}
			if echFresh, _, rErr := state.get(ctx, *dnsAddr, *targetHost, true); rErr == nil {
				return dialOnce(echFresh)
			}
		}
		return conn, err
	}

	transport := &http.Transport{
		DialTLSContext:        dialTLSContext,
		ForceAttemptHTTP2:     true,
		MaxIdleConns:          32,
		IdleConnTimeout:       90 * time.Second,
		TLSHandshakeTimeout:   10 * time.Second,
		ExpectContinueTimeout: 1 * time.Second,
		ResponseHeaderTimeout: 0,
	}

	proxy := httputil.NewSingleHostReverseProxy(targetURL)
	proxy.Transport = transport
	proxy.FlushInterval = -1 // Flush immediately for SSE streaming
	origDirector := proxy.Director
	proxy.Director = func(req *http.Request) {
		origDirector(req)
		req.Host = *targetHost
	}

	log.Printf("dragtokens-ech-proxy listening on http://%s -> https://%s (DNS %s)", *listenAddr, *targetHost, *dnsAddr)
	srv := &http.Server{
		Addr:              *listenAddr,
		Handler:           proxy,
		ReadHeaderTimeout: 15 * time.Second,
	}
	if err := srv.ListenAndServe(); err != nil {
		log.Fatalf("server failed: %v", err)
	}
}
