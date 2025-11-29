# Accela OAuth Diagnostic Probe

A standalone diagnostic tool to systematically test Accela OAuth flows and identify the root cause of authentication failures.

## Features

- **Preflight Check**: Verify network connectivity to Accela endpoints
- **App Credentials Check**: Validate your Accela app registration
- **Environment Check**: Verify agency and environment availability
- **Password Grant Testing**: Test token issuance in both sandbox and production
- **Authorization Code Flow**: Generate auth URLs and test token exchange variants
- **Comprehensive Reporting**: JSON reports with redacted sensitive data

## Setup

1. Create a virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your credentials
```

## Usage

### Run All Tests

Generate a complete diagnostic report:
```bash
python probe.py run-all
```

This will:
- Check connectivity
- Validate app credentials
- Test HCFL/PROD environment
- Test sandbox password grant
- Test HCFL/PROD password grant
- Generate a JSON report in `runs/`

### Individual Commands

**Preflight Check**:
```bash
python probe.py preflight
```

**App Credentials Check**:
```bash
python probe.py app-creds-check
```

**Environment Check**:
```bash
python probe.py env-check --agency HCFL --env PROD
```

**Password Token (Sandbox)**:
```bash
python probe.py password-token --agency nullisland --env TEST
```

**Password Token (HCFL/PROD)**:
```bash
python probe.py password-token --agency HCFL --env PROD
```

**Authorization Code Flow**:
```bash
# Generate authorization URL
python probe.py authorize --redirect local --pkce

# After user logs in, exchange code for tokens
python probe.py exchange-code --code YOUR_AUTH_CODE
```

## Output

Reports are saved in `runs/<timestamp>/report.json` with:
- Test summaries (PASS/FAIL for each test)
- Detailed results (request/response data)
- Diagnostic conclusion
- Actionable recommendations
- All sensitive data redacted

## Exit Codes

- `0`: Test passed
- `1`: Test failed

## Security

All sensitive data (secrets, passwords, tokens) are automatically redacted in:
- Console output
- JSON reports
- Log files

Client IDs, agency names, and environments are visible (not sensitive).
