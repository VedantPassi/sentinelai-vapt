# Test Targets

Spin up vulnerable targets locally for scanning tests.

## DVWA (Damn Vulnerable Web Application)

```bash
docker run -d -p 8080:80 vulnerables/web-dvwa
```

Access: http://localhost:8080  
Default creds: `admin` / `password`

## OWASP Juice Shop

```bash
docker run -d -p 3000:3000 bkimminich/juice-shop
```

Access: http://localhost:3000

## Usage

Point SentinelAI scan targets at these URLs during Phase 2 integration testing.  
Never scan external or production systems without explicit authorization.
