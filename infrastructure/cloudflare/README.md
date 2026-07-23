# Cloudflare Deployment Guide

## Overview

This document describes how to deploy Pepe behind Cloudflare for production use.

## DNS Configuration

1. Add an A record pointing to your origin server IP
2. Enable Proxy status (orange cloud) for the main domain
3. Add CNAME records for subdomains if needed

## SSL/TLS Settings

- **SSL/TLS encryption mode**: Full (Strict)
- **Always Use HTTPS**: Enabled
- **Minimum TLS version**: 1.2
- **Automatic HTTPS Rewrites**: Enabled

## Origin Certificate

1. Go to SSL/TLS > Origin Server
2. Create an Origin Certificate
3. Install the certificate on your origin server
4. Set certificate validity to 15 years

## WAF Rules

Create custom rules to protect your API:

```
(http.request.uri.path contains "/api/v1/auth") or
(http.request.uri.path contains "/api/v1/users")
```

Actions:
- **Security Level**: High
- **Browser Integrity Check**: Enabled
- **Challenge Passage**: 30 minutes

## Rate Limiting

Create rate limiting rules for API endpoints:

| Path Pattern | Requests per 10 minutes | Action |
|---|---|---|
| `/api/*` | 100 | Block |
| `/api/v1/auth/*` | 10 | Block |

## Cache Rules

### Static Assets

- **Cache everything**: Enabled
- **Edge TTL**: 1 month
- **Browser TTL**: 1 year

### API Endpoints

- **Bypass cache**: Enabled for `/api/*`
- **Cache key**: Include cookies

### Auth Routes

- **Bypass cache**: Enabled for `/api/v1/auth/*`
- **Security level**: High

## Security Headers

Add the following headers via Transform Rules:

| Header | Value |
|---|---|
| X-Content-Type-Options | nosniff |
| X-Frame-Options | DENY |
| Referrer-Policy | strict-origin-when-cross-origin |
| Permissions-Policy | camera=(), microphone=(), geolocation=() |

## Credentials Storage

**DO NOT** store secrets in Cloudflare:

- Use Environment Variables for API tokens
- Store origin certificates in a secrets manager
- Rotate API keys regularly
- Use Cloudflare Access for sensitive dashboards

## Monitoring

- Enable Cloudflare Analytics
- Set up alerts for unusual traffic patterns
- Monitor WAF rule triggers
- Review cache hit rates

## Cost Optimization

- Enable Argo Smart Routing for faster routing
- Use Cloudflare Workers for edge computing
- Enable Polish for image optimization
- Consider Cloudflare Images for user-uploaded content
