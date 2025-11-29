#!/usr/bin/env python3
"""Accela OAuth Diagnostic Probe CLI."""
import os
import sys
import argparse
from dotenv import load_dotenv
from datetime import datetime

from lib.preflight import run_preflight_check
from lib.app_creds import check_app_credentials
from lib.env_check import check_environment
from lib.password_token import test_password_grant
from lib.auth_code import generate_authorization_url
from lib.token_exchange import test_token_exchange_variants
from lib.report import generate_report, save_report, print_summary


def load_config():
    """Load configuration from .env file."""
    load_dotenv()

    config = {
        "client_id": os.getenv("ACCELA_CLIENT_ID"),
        "client_secret": os.getenv("ACCELA_CLIENT_SECRET"),
        "auth_base": os.getenv("ACCELA_AUTH_BASE", "https://auth.accela.com"),
        "api_base": os.getenv("ACCELA_API_BASE", "https://apis.accela.com"),
        "agency": os.getenv("ACCELA_AGENCY", "HCFL"),
        "environment": os.getenv("ACCELA_ENVIRONMENT", "PROD"),
        "scope": os.getenv("ACCELA_SCOPE", "records"),
        "redirect_uri_local": os.getenv("ACCELA_REDIRECT_URI_LOCAL"),
        "redirect_uri_prod": os.getenv("ACCELA_REDIRECT_URI_PROD"),
        "test_username": os.getenv("ACCELA_TEST_USERNAME", "developer"),
        "test_password": os.getenv("ACCELA_TEST_PASSWORD", "accela"),
        "hcfl_username": os.getenv("ACCELA_HCFL_USERNAME"),
        "hcfl_password": os.getenv("ACCELA_HCFL_PASSWORD")
    }

    # Validate required fields
    if not config["client_id"] or not config["client_secret"]:
        print("❌ Error: ACCELA_CLIENT_ID and ACCELA_CLIENT_SECRET must be set in .env")
        sys.exit(1)

    return config


def cmd_preflight(args, config):
    """Run preflight connectivity checks."""
    print("\n" + "="*60)
    print("PREFLIGHT CHECK")
    print("="*60 + "\n")

    results = run_preflight_check(config["auth_base"], config["api_base"])

    print("\n" + "="*60)
    print(f"Status: {results['overall_status']}")
    print("="*60 + "\n")

    return results["overall_status"] == "PASS"


def cmd_app_creds_check(args, config):
    """Check app credentials."""
    print("\n" + "="*60)
    print("APP CREDENTIALS CHECK")
    print("="*60 + "\n")

    results = check_app_credentials(
        config["api_base"],
        config["client_id"],
        config["client_secret"]
    )

    print("\n" + "="*60)
    print(f"Status: {'PASS' if results['success'] else 'FAIL'}")
    print("="*60 + "\n")

    return results["success"]


def cmd_env_check(args, config):
    """Check agency and environment."""
    agency = args.agency or config["agency"]
    env = args.env or config["environment"]

    print("\n" + "="*60)
    print(f"ENVIRONMENT CHECK: {agency}/{env}")
    print("="*60 + "\n")

    results = check_environment(
        config["api_base"],
        config["client_id"],
        config["client_secret"],
        agency,
        env
    )

    print("\n" + "="*60)
    print(f"Status: {'PASS' if results['success'] else 'FAIL'}")
    print("="*60 + "\n")

    return results["success"]


def cmd_password_token(args, config):
    """Test password grant token."""
    agency = args.agency or config["agency"]
    env = args.env or config["environment"]

    # Determine which credentials to use
    if agency.lower() == "nullisland" or env.lower() == "test":
        username = config["test_username"]
        password = config["test_password"]
        agency = "nullisland"
        env = "TEST"
    else:
        username = config["hcfl_username"]
        password = config["hcfl_password"]
        if not username or not password:
            print("❌ Error: ACCELA_HCFL_USERNAME and ACCELA_HCFL_PASSWORD must be set in .env")
            return False

    print("\n" + "="*60)
    print(f"PASSWORD GRANT TEST: {agency}/{env}")
    print("="*60 + "\n")

    results = test_password_grant(
        config["auth_base"],
        config["client_id"],
        config["client_secret"],
        agency,
        env,
        username,
        password,
        config["scope"]
    )

    print("\n" + "="*60)
    print(f"Status: {'PASS' if results['success'] else 'FAIL'}")
    print("="*60 + "\n")

    return results["success"]


def cmd_authorize(args, config):
    """Generate authorization URL."""
    redirect_uri = config["redirect_uri_local"] if args.redirect == "local" else config["redirect_uri_prod"]

    if not redirect_uri:
        print("❌ Error: Redirect URI not configured in .env")
        return False

    print("\n" + "="*60)
    print("AUTHORIZATION URL")
    print("="*60 + "\n")

    result = generate_authorization_url(
        config["auth_base"],
        config["client_id"],
        redirect_uri,
        config["agency"],
        config["environment"],
        config["scope"],
        use_pkce=args.pkce
    )

    print(f"Authorization URL:\n{result['url']}\n")
    print(f"State: {result['state']}")
    if 'code_verifier' in result:
        print(f"Code Verifier: {result['code_verifier']}")
        print("\n⚠️  Save the code_verifier - you'll need it for exchange-code command")

    print("\n" + "="*60)
    print("Open this URL in a browser to log in and get the authorization code.")
    print("="*60 + "\n")

    return True


def cmd_exchange_code(args, config):
    """Exchange authorization code for tokens."""
    if not args.code:
        print("❌ Error: --code is required")
        return False

    redirect_uri = config["redirect_uri_local"] if args.redirect == "local" else config["redirect_uri_prod"]

    print("\n" + "="*60)
    print("TOKEN EXCHANGE - TESTING VARIANTS")
    print("="*60 + "\n")

    results = test_token_exchange_variants(
        config["auth_base"],
        config["client_id"],
        config["client_secret"],
        args.code,
        redirect_uri,
        agency=config["agency"],
        environment=config["environment"],
        code_verifier=args.code_verifier
    )

    # Check if any variant succeeded
    success = any(r["success"] for r in results)

    return success


def cmd_run_all(args, config):
    """Run all diagnostic tests."""
    print("\n" + "="*80)
    print(" "*20 + "ACCELA OAUTH DIAGNOSTIC PROBE")
    print("="*80 + "\n")

    summary = {}
    details = {}
    recommendations = []

    # 1. Preflight check
    print("\n[1/5] Running preflight check...")
    preflight_result = run_preflight_check(config["auth_base"], config["api_base"])
    summary["preflight"] = preflight_result["overall_status"]
    details["preflight"] = preflight_result

    # 2. App credentials check
    print("\n[2/5] Checking app credentials...")
    app_creds_result = check_app_credentials(
        config["api_base"],
        config["client_id"],
        config["client_secret"]
    )
    summary["app_creds_check"] = "PASS" if app_creds_result["success"] else "FAIL"
    details["app_creds"] = app_creds_result

    # 3. Environment check
    print("\n[3/5] Checking HCFL/PROD environment...")
    env_result = check_environment(
        config["api_base"],
        config["client_id"],
        config["client_secret"],
        config["agency"],
        config["environment"]
    )
    summary[f"env_check_{config['agency']}_{config['environment']}"] = "PASS" if env_result["success"] else "FAIL"
    details["env_check"] = env_result

    # 4. Sandbox password token
    print("\n[4/5] Testing sandbox password grant...")
    sandbox_result = test_password_grant(
        config["auth_base"],
        config["client_id"],
        config["client_secret"],
        "nullisland",
        "TEST",
        config["test_username"],
        config["test_password"],
        config["scope"]
    )
    summary["password_token_sandbox"] = "PASS" if sandbox_result["success"] else "FAIL"
    details["password_token_sandbox"] = sandbox_result

    # 5. HCFL/PROD password token
    print("\n[5/5] Testing HCFL/PROD password grant...")
    if config["hcfl_username"] and config["hcfl_password"]:
        hcfl_result = test_password_grant(
            config["auth_base"],
            config["client_id"],
            config["client_secret"],
            config["agency"],
            config["environment"],
            config["hcfl_username"],
            config["hcfl_password"],
            config["scope"]
        )
        summary["password_token_HCFL"] = "PASS" if hcfl_result["success"] else "FAIL"
        details["password_token_HCFL"] = hcfl_result
    else:
        summary["password_token_HCFL"] = "SKIPPED"
        details["password_token_HCFL"] = {"error": "No HCFL credentials provided"}

    # Generate conclusion and recommendations
    conclusion = _generate_conclusion(summary, details)
    recommendations = _generate_recommendations(summary, details)

    # Print summary
    print_summary(summary)

    # Generate and save report
    report = generate_report(summary, details, conclusion, recommendations)
    output_dir = os.path.join(os.path.dirname(__file__), "runs", datetime.utcnow().strftime('%Y%m%d_%H%M%S'))
    report_path = save_report(report, output_dir)

    print(f"\n📄 Full report saved to: {report_path}")
    print(f"\n💡 Conclusion: {conclusion}")
    print(f"\n📋 Recommendations:")
    for i, rec in enumerate(recommendations, 1):
        print(f"   {i}. {rec}")

    print("\n" + "="*80 + "\n")

    return True


def _generate_conclusion(summary: dict, details: dict) -> str:
    """Generate diagnostic conclusion based on test results."""
    # Check what passed and failed
    preflight_pass = summary.get("preflight") == "PASS"
    app_creds_pass = summary.get("app_creds_check") == "PASS"
    env_pass = "PASS" in summary.get("env_check_HCFL_PROD", "FAIL")
    sandbox_pass = summary.get("password_token_sandbox") == "PASS"
    hcfl_pass = summary.get("password_token_HCFL") == "PASS"

    if not preflight_pass:
        return "Network connectivity issue - cannot reach Accela endpoints"

    if not app_creds_pass:
        return "App credentials are invalid or app is not properly registered"

    if not env_pass:
        return "HCFL/PROD agency or environment does not exist or is not available"

    if sandbox_pass and not hcfl_pass:
        return "App credentials valid, sandbox tokens work, but HCFL/PROD token exchange fails - likely HCFL-specific configuration issue"

    if not sandbox_pass and not hcfl_pass:
        return "Token endpoint fails for both sandbox and HCFL - likely app configuration or permission issue"

    if hcfl_pass:
        return "All tests passed - OAuth flow should work"

    return "Unable to determine root cause - review detailed test results"


def _generate_recommendations(summary: dict, details: dict) -> list:
    """Generate recommendations based on test results."""
    recommendations = []

    if summary.get("app_creds_check") == "FAIL":
        recommendations.append("Verify app credentials in Accela developer portal")

    if "FAIL" in summary.get("env_check_HCFL_PROD", ""):
        recommendations.append("Contact HCFL administrator to verify agency/environment configuration")

    if summary.get("password_token_sandbox") == "PASS" and summary.get("password_token_HCFL") == "FAIL":
        recommendations.append("Contact HCFL admin to verify app is enabled for their agency")
        recommendations.append("Try test/sandbox environment first for development")

        # Extract trace ID if available
        hcfl_details = details.get("password_token_HCFL", {})
        if hcfl_details.get("trace_id"):
            recommendations.append(f"Provide trace_id to Accela support: {hcfl_details['trace_id']}")

    if summary.get("password_token_sandbox") == "FAIL":
        recommendations.append("App may not have correct permissions - check app scope configuration")

    if not recommendations:
        recommendations.append("All tests passed - proceed with authorization code flow")

    return recommendations


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Accela OAuth Diagnostic Probe")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Preflight command
    subparsers.add_parser("preflight", help="Run preflight connectivity checks")

    # App credentials check
    subparsers.add_parser("app-creds-check", help="Validate app credentials")

    # Environment check
    env_parser = subparsers.add_parser("env-check", help="Check agency and environment")
    env_parser.add_argument("--agency", help="Agency code (default: from .env)")
    env_parser.add_argument("--env", help="Environment (default: from .env)")

    # Password token
    pwd_parser = subparsers.add_parser("password-token", help="Test password grant flow")
    pwd_parser.add_argument("--agency", help="Agency code (use 'nullisland' for sandbox)")
    pwd_parser.add_argument("--env", help="Environment (use 'TEST' for sandbox)")

    # Authorize
    auth_parser = subparsers.add_parser("authorize", help="Generate authorization URL")
    auth_parser.add_argument("--redirect", choices=["local", "prod"], default="local", help="Redirect URI to use")
    auth_parser.add_argument("--pkce", action="store_true", help="Use PKCE")

    # Exchange code
    exchange_parser = subparsers.add_parser("exchange-code", help="Exchange authorization code for tokens")
    exchange_parser.add_argument("--code", required=True, help="Authorization code from callback")
    exchange_parser.add_argument("--redirect", choices=["local", "prod"], default="local", help="Redirect URI used")
    exchange_parser.add_argument("--code-verifier", help="PKCE code verifier (if used)")

    # Run all
    subparsers.add_parser("run-all", help="Run all diagnostic tests and generate report")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Load configuration
    config = load_config()

    # Execute command
    commands = {
        "preflight": cmd_preflight,
        "app-creds-check": cmd_app_creds_check,
        "env-check": cmd_env_check,
        "password-token": cmd_password_token,
        "authorize": cmd_authorize,
        "exchange-code": cmd_exchange_code,
        "run-all": cmd_run_all
    }

    success = commands[args.command](args, config)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
