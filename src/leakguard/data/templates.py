"""Catalog of author-written template families for synthetic data generation.

Covers 15 distinct families across 3 message-risk categories:
- high_risk_exposure: credentials, active tokens, full payment cards, DB dumps
- possible_exposure: personal contact details, domestic banking, Indian identity
- no_exposure: safe placeholders, RFC documentation domains, decoys, policy copy

Templates use structured segment definitions to ensure 100% exact character offset alignment.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

# A segment is either:
# 1. str: static text literal
Segment = str | tuple[str, str | None]


@dataclass(frozen=True)
class Template:
    template_id: str
    family_id: str
    message_label: str  # no_exposure | possible_exposure | high_risk_exposure
    segments: tuple[Segment, ...]


def _t(
    template_id: str,
    family_id: str,
    message_label: str,
    segments: Sequence[Segment],
) -> Template:
    return Template(
        template_id=template_id,
        family_id=family_id,
        message_label=message_label,
        segments=tuple(segments),
    )


# -----------------------------------------------------------------------------
# 1. fam_cloud_infra (HIGH RISK) - 11 templates
# -----------------------------------------------------------------------------
_FAM_CLOUD_INFRA = [
    _t(
        "tpl_cloud_01",
        "fam_cloud_infra",
        "high_risk_exposure",
        [
            "AWS credentials for prod migration: AWS_ACCESS_KEY_ID=",
            ("api_key", "API_KEY"),
            " and secret password=",
            ("password", "PASSWORD"),
            ". Do not commit!",
        ],
    ),
    _t(
        "tpl_cloud_02",
        "fam_cloud_infra",
        "high_risk_exposure",
        [
            "Database connection string failed. Using fallback: postgres://postgres:",
            ("password", "PASSWORD"),
            "@db.internal-cloud.in:5432/primary_db",
        ],
    ),
    _t(
        "tpl_cloud_03",
        "fam_cloud_infra",
        "high_risk_exposure",
        [
            "Exported cloud token for CI deployment: export CLOUD_AUTH_TOKEN=",
            ("api_key", "API_KEY"),
        ],
    ),
    _t(
        "tpl_cloud_04",
        "fam_cloud_infra",
        "high_risk_exposure",
        [
            "Temporary Redis cluster master password is: ",
            ("password", "PASSWORD"),
            ". Please rotate after deployment.",
        ],
    ),
    _t(
        "tpl_cloud_05",
        "fam_cloud_infra",
        "high_risk_exposure",
        [
            "Kubernetes secret manifest patch:\n  auth_token: ",
            ("api_key", "API_KEY"),
            "\n  db_master_pass: ",
            ("password", "PASSWORD"),
        ],
    ),
    _t(
        "tpl_cloud_06",
        "fam_cloud_infra",
        "high_risk_exposure",
        [
            "Staging microservice config:\nAPI_GATEWAY_KEY=",
            ("api_key", "API_KEY"),
            "\nNOTIFICATION_PASS=",
            ("password", "PASSWORD"),
        ],
    ),
    _t(
        "tpl_cloud_07",
        "fam_cloud_infra",
        "high_risk_exposure",
        [
            'Terraform state output shows unencrypted s3_api_key = "',
            ("api_key", "API_KEY"),
            '" and admin pass "',
            ("password", "PASSWORD"),
            '".',
        ],
    ),
    _t(
        "tpl_cloud_08",
        "fam_cloud_infra",
        "high_risk_exposure",
        [
            "GCP service account private token: ",
            ("api_key", "API_KEY"),
            " granted role roles/owner on project apex-prod.",
        ],
    ),
    _t(
        "tpl_cloud_09",
        "fam_cloud_infra",
        "high_risk_exposure",
        [
            "RabbitMQ credentials for telemetry worker: amqp://admin:",
            ("password", "PASSWORD"),
            "@queue.internal-cloud.in:5672/vhost",
        ],
    ),
    _t(
        "tpl_cloud_10",
        "fam_cloud_infra",
        "high_risk_exposure",
        ["Elasticsearch cluster API key generated for log forwarder: ", ("api_key", "API_KEY")],
    ),
    _t(
        "tpl_cloud_11",
        "fam_cloud_infra",
        "high_risk_exposure",
        [
            "Production MongoDB connection URL:\nmongodb://cluster_admin:",
            ("password", "PASSWORD"),
            "@mongo-01.internal-cloud.in:27017/prod_catalog?authSource=admin",
        ],
    ),
]

# -----------------------------------------------------------------------------
# 2. fam_credentials_chat (HIGH RISK) - 11 templates
# -----------------------------------------------------------------------------
_FAM_CRED_CHAT = [
    _t(
        "tpl_chat_01",
        "fam_credentials_chat",
        "high_risk_exposure",
        [
            "Hey, here is the temporary staging password you asked for: ",
            ("password", "PASSWORD"),
            ". Let me know once logged in.",
        ],
    ),
    _t(
        "tpl_chat_02",
        "fam_credentials_chat",
        "high_risk_exposure",
        [
            "Quick fix for the build failure: use personal access token `",
            ("api_key", "API_KEY"),
            "` to pull private dependencies.",
        ],
    ),
    _t(
        "tpl_chat_03",
        "fam_credentials_chat",
        "high_risk_exposure",
        [
            "Can someone test the webhook with this bot token? Token: ",
            ("api_key", "API_KEY"),
            " on channel #dev-alerts.",
        ],
    ),
    _t(
        "tpl_chat_04",
        "fam_credentials_chat",
        "high_risk_exposure",
        [
            "Shared root credentials for testbed server: username=devroot password=",
            ("password", "PASSWORD"),
            ". Don't share outside team.",
        ],
    ),
    _t(
        "tpl_chat_05",
        "fam_credentials_chat",
        "high_risk_exposure",
        [
            "VPN access credentials:\nUser: ",
            ("email", "EMAIL"),
            "\nPassword: ",
            ("password", "PASSWORD"),
            "\nServer: vpn.internal-cloud.in",
        ],
    ),
    _t(
        "tpl_chat_06",
        "fam_credentials_chat",
        "high_risk_exposure",
        [
            "Slack webhook URL has an embedded secret: ",
            ("api_key", "API_KEY"),
            ". Please do not paste in public channels.",
        ],
    ),
    _t(
        "tpl_chat_07",
        "fam_credentials_chat",
        "high_risk_exposure",
        [
            "I reset the test admin account. The new temporary password is `",
            ("password", "PASSWORD"),
            "`. Please change it immediately.",
        ],
    ),
    _t(
        "tpl_chat_08",
        "fam_credentials_chat",
        "high_risk_exposure",
        [
            "Auth header for our external partner integration:\nAuthorization: ",
            ("api_key", "API_KEY"),
        ],
    ),
    _t(
        "tpl_chat_09",
        "fam_credentials_chat",
        "high_risk_exposure",
        [
            "Hey ",
            ("name", "PERSON"),
            ", left the staging DB password as ",
            ("password", "PASSWORD"),
            " in case you need to run queries tonight.",
        ],
    ),
    _t(
        "tpl_chat_10",
        "fam_credentials_chat",
        "high_risk_exposure",
        [
            "Grafana metrics viewer pass is: ",
            ("password", "PASSWORD"),
            ". URL: https://metrics.internal-cloud.in",
        ],
    ),
    _t(
        "tpl_chat_11",
        "fam_credentials_chat",
        "high_risk_exposure",
        [
            "Here are the Stripe test webhook secrets for the sandbox:\nSTRIPE_SECRET_KEY=",
            ("api_key", "API_KEY"),
            "\nSTRIPE_SIGNING_SECRET=",
            ("password", "PASSWORD"),
        ],
    ),
]

# -----------------------------------------------------------------------------
# 3. fam_credentials_git (HIGH RISK) - 10 templates
# -----------------------------------------------------------------------------
_FAM_CRED_GIT = [
    _t(
        "tpl_git_01",
        "fam_credentials_git",
        "high_risk_exposure",
        [
            'fix(auth): update hardcoded API key for smoke testing: api_key = "',
            ("api_key", "API_KEY"),
            '"',
        ],
    ),
    _t(
        "tpl_git_02",
        "fam_credentials_git",
        "high_risk_exposure",
        ["WIP: accidental commit of local env file with DB_PASSWORD=", ("password", "PASSWORD")],
    ),
    _t(
        "tpl_git_03",
        "fam_credentials_git",
        "high_risk_exposure",
        [
            "Merge branch 'hotfix/token-refresh'\nCommit includes master secret: ",
            ("api_key", "API_KEY"),
        ],
    ),
    _t(
        "tpl_git_04",
        "fam_credentials_git",
        "high_risk_exposure",
        [
            'Revert "remove staging secrets"\nRestores credentials:\nAPI_TOKEN = \'',
            ("api_key", "API_KEY"),
            "'\nSECRET_PASS = '",
            ("password", "PASSWORD"),
            "'",
        ],
    ),
    _t(
        "tpl_git_05",
        "fam_credentials_git",
        "high_risk_exposure",
        [
            "docs: update deployment README with admin password for docker: `",
            ("password", "PASSWORD"),
            "`",
        ],
    ),
    _t(
        "tpl_git_06",
        "fam_credentials_git",
        "high_risk_exposure",
        [
            "chore(config): add default secrets file for local Docker container. password: ",
            ("password", "PASSWORD"),
        ],
    ),
    _t(
        "tpl_git_07",
        "fam_credentials_git",
        "high_risk_exposure",
        ["ci(github): add workflow with embedded deploy token: ", ("api_key", "API_KEY")],
    ),
    _t(
        "tpl_git_08",
        "fam_credentials_git",
        "high_risk_exposure",
        [
            "debug: temporarily logging bearer token in auth middleware: Authorization: ",
            ("api_key", "API_KEY"),
        ],
    ),
    _t(
        "tpl_git_09",
        "fam_credentials_git",
        "high_risk_exposure",
        [
            "feat(backup): automated s3 backup script with hardcoded aws_access_key: ",
            ("api_key", "API_KEY"),
        ],
    ),
    _t(
        "tpl_git_10",
        "fam_credentials_git",
        "high_risk_exposure",
        [
            "test: mock integration test with real staging token: ",
            ("api_key", "API_KEY"),
            " and pass ",
            ("password", "PASSWORD"),
        ],
    ),
]

# -----------------------------------------------------------------------------
# 4. fam_fin_cards (HIGH RISK) - 11 templates
# -----------------------------------------------------------------------------
_FAM_FIN_CARDS = [
    _t(
        "tpl_card_01",
        "fam_fin_cards",
        "high_risk_exposure",
        [
            "Customer requested manual charge. Card number: ",
            ("card_number", "CARD"),
            ", Exp: 09/28, CVV: 481, Name: ",
            ("name", "PERSON"),
            ".",
        ],
    ),
    _t(
        "tpl_card_02",
        "fam_fin_cards",
        "high_risk_exposure",
        [
            "Payment gateway error log: failed transaction on card ",
            ("card_number", "CARD"),
            " for amount INR 12,450.",
        ],
    ),
    _t(
        "tpl_card_03",
        "fam_fin_cards",
        "high_risk_exposure",
        [
            "Corporate expense card details for travel reimbursement: ",
            ("card_number", "CARD"),
            ", holder ",
            ("name", "PERSON"),
            ".",
        ],
    ),
    _t(
        "tpl_card_04",
        "fam_fin_cards",
        "high_risk_exposure",
        [
            "Unmasked credit card dumped in error response: card_number=",
            ("card_number", "CARD"),
            " response_code=DECLINED",
        ],
    ),
    _t(
        "tpl_card_05",
        "fam_fin_cards",
        "high_risk_exposure",
        [
            "Billing update ticket:\nCard: ",
            ("card_number", "CARD"),
            "\nBilling contact: ",
            ("email", "EMAIL"),
            "\nPhone: ",
            ("phone", "PHONE"),
        ],
    ),
    _t(
        "tpl_card_06",
        "fam_fin_cards",
        "high_risk_exposure",
        [
            "Merchant chargeback alert: Disputed transaction on card ",
            ("card_number", "CARD"),
            " by cardholder ",
            ("name", "PERSON"),
            ".",
        ],
    ),
    _t(
        "tpl_card_07",
        "fam_fin_cards",
        "high_risk_exposure",
        [
            "POS terminal raw receipt copy: CARD NUM: ",
            ("card_number", "CARD"),
            " AUTH_CODE: 928194 AMT: INR 4,999.00",
        ],
    ),
    _t(
        "tpl_card_08",
        "fam_fin_cards",
        "high_risk_exposure",
        [
            'Debug checkout payload:\n{"credit_card": "',
            ("card_number", "CARD"),
            '", "customer": "',
            ("name", "PERSON"),
            '", "cvv": "382"}',
        ],
    ),
    _t(
        "tpl_card_09",
        "fam_fin_cards",
        "high_risk_exposure",
        [
            "Hotel booking confirmation: Card charged: ",
            ("card_number", "CARD"),
            ", guest contact: ",
            ("phone", "PHONE"),
            ".",
        ],
    ),
    _t(
        "tpl_card_10",
        "fam_fin_cards",
        "high_risk_exposure",
        [
            "Subscription renewal failure for card ",
            ("card_number", "CARD"),
            ". Please reach out to user at ",
            ("email", "EMAIL"),
            ".",
        ],
    ),
    _t(
        "tpl_card_11",
        "fam_fin_cards",
        "high_risk_exposure",
        [
            "Payment transaction raw record: Card: ",
            ("card_number", "CARD"),
            " | Name: ",
            ("name", "PERSON"),
            " | Phone: ",
            ("phone", "PHONE"),
        ],
    ),
]

# -----------------------------------------------------------------------------
# 5. fam_dev_logs (HIGH RISK) - 10 templates
# -----------------------------------------------------------------------------
_FAM_DEV_LOGS = [
    _t(
        "tpl_log_01",
        "fam_dev_logs",
        "high_risk_exposure",
        [
            "[ERROR] HTTP 500 in /api/v1/auth - Failed header parse: Authorization: ",
            ("api_key", "API_KEY"),
            " - stack trace dumped.",
        ],
    ),
    _t(
        "tpl_log_02",
        "fam_dev_logs",
        "high_risk_exposure",
        ["[DEBUG] Database connection pool initialized with password: ", ("password", "PASSWORD")],
    ),
    _t(
        "tpl_log_03",
        "fam_dev_logs",
        "high_risk_exposure",
        [
            "[FATAL] Auth failure: user=",
            ("email", "EMAIL"),
            " attempted login with password=",
            ("password", "PASSWORD"),
        ],
    ),
    _t(
        "tpl_log_04",
        "fam_dev_logs",
        "high_risk_exposure",
        [
            "[INFO] Outgoing webhook triggered with token: ",
            ("api_key", "API_KEY"),
            " to target endpoint.",
        ],
    ),
    _t(
        "tpl_log_05",
        "fam_dev_logs",
        "high_risk_exposure",
        [
            "[WARN] Insecure parameter logged: /user/update?token=",
            ("api_key", "API_KEY"),
            "&email=",
            ("email", "EMAIL"),
        ],
    ),
    _t(
        "tpl_log_06",
        "fam_dev_logs",
        "high_risk_exposure",
        [
            "[ERROR] Redis connection timeout: redis://:",
            ("password", "PASSWORD"),
            "@cache-prod.internal-cloud.in:6379/0",
        ],
    ),
    _t(
        "tpl_log_07",
        "fam_dev_logs",
        "high_risk_exposure",
        [
            "Exception in thread 'pool-2': java.sql.SQLException: Access denied for user 'root'@'%' using password '",
            ("password", "PASSWORD"),
            "'",
        ],
    ),
    _t(
        "tpl_log_08",
        "fam_dev_logs",
        "high_risk_exposure",
        [
            '[DEBUG] Request payload dumped: {"token": "',
            ("api_key", "API_KEY"),
            '", "admin_secret": "',
            ("password", "PASSWORD"),
            '"}',
        ],
    ),
    _t(
        "tpl_log_09",
        "fam_dev_logs",
        "high_risk_exposure",
        ["[TRACE] AWS S3 PutObject request with AccessKeyId=", ("api_key", "API_KEY")],
    ),
    _t(
        "tpl_log_10",
        "fam_dev_logs",
        "high_risk_exposure",
        ["[WARN] JWT verification failed for Bearer token: ", ("api_key", "API_KEY")],
    ),
]

# -----------------------------------------------------------------------------
# 6. fam_identity_in (POSSIBLE EXPOSURE) - 11 templates
# -----------------------------------------------------------------------------
_FAM_IDENTITY_IN = [
    _t(
        "tpl_id_01",
        "fam_identity_in",
        "possible_exposure",
        [
            "Aadhaar verification request for applicant ",
            ("name", "PERSON"),
            ": Aadhaar Number: ",
            ("aadhaar", "AADHAAR"),
            ". Status: PENDING.",
        ],
    ),
    _t(
        "tpl_id_02",
        "fam_identity_in",
        "possible_exposure",
        [
            "Tax deduction document attached: PAN: ",
            ("pan", "PAN"),
            " belonging to taxpayer ",
            ("name", "PERSON"),
            ".",
        ],
    ),
    _t(
        "tpl_id_03",
        "fam_identity_in",
        "possible_exposure",
        [
            "KYC document record:\nName: ",
            ("name", "PERSON"),
            "\nAadhaar: ",
            ("aadhaar", "AADHAAR"),
            "\nPAN: ",
            ("pan", "PAN"),
        ],
    ),
    _t(
        "tpl_id_04",
        "fam_identity_in",
        "possible_exposure",
        [
            "Voter ID details submitted for electoral verification: EPIC: ",
            ("voter_id", "VOTER_ID"),
            ", Citizen: ",
            ("name", "PERSON"),
            ".",
        ],
    ),
    _t(
        "tpl_id_05",
        "fam_identity_in",
        "possible_exposure",
        [
            "Employee onboarding KYC update: PAN card ",
            ("pan", "PAN"),
            " verified against ITD database for ",
            ("name", "PERSON"),
            ".",
        ],
    ),
    _t(
        "tpl_id_06",
        "fam_identity_in",
        "possible_exposure",
        [
            "Customer identity mismatch: Provided Aadhaar ",
            ("aadhaar", "AADHAAR"),
            " does not match registered phone ",
            ("phone", "PHONE"),
            ".",
        ],
    ),
    _t(
        "tpl_id_07",
        "fam_identity_in",
        "possible_exposure",
        [
            "Account opening intake:\nName: ",
            ("name", "PERSON"),
            "\nUIDAI No: ",
            ("aadhaar", "AADHAAR"),
            "\nContact: ",
            ("email", "EMAIL"),
        ],
    ),
    _t(
        "tpl_id_08",
        "fam_identity_in",
        "possible_exposure",
        [
            "TDS certificate generated for PAN: ",
            ("pan", "PAN"),
            ". Sent copy to email: ",
            ("email", "EMAIL"),
            ".",
        ],
    ),
    _t(
        "tpl_id_09",
        "fam_identity_in",
        "possible_exposure",
        [
            "Voter registration update acknowledgment for EPIC ",
            ("voter_id", "VOTER_ID"),
            ", voter name: ",
            ("name", "PERSON"),
            ", mobile: ",
            ("phone", "PHONE"),
            ".",
        ],
    ),
    _t(
        "tpl_id_10",
        "fam_identity_in",
        "possible_exposure",
        [
            "Verification audit: Customer submitted Aadhaar ",
            ("aadhaar", "AADHAAR"),
            " along with PAN ",
            ("pan", "PAN"),
            " for loan approval.",
        ],
    ),
    _t(
        "tpl_id_11",
        "fam_identity_in",
        "possible_exposure",
        [
            "Government ID record: Candidate ",
            ("name", "PERSON"),
            " provided PAN ",
            ("pan", "PAN"),
            " and Aadhaar ",
            ("aadhaar", "AADHAAR"),
            ".",
        ],
    ),
]

# -----------------------------------------------------------------------------
# 7. fam_banking_in (POSSIBLE EXPOSURE) - 11 templates
# -----------------------------------------------------------------------------
_FAM_BANKING_IN = [
    _t(
        "tpl_bank_01",
        "fam_banking_in",
        "possible_exposure",
        [
            "Please transfer reimbursement via NEFT to Account: ",
            ("account_number", "ACCOUNT_NUMBER"),
            " with IFSC: ",
            ("ifsc", "None"),
            ", Beneficiary: ",
            ("name", "PERSON"),
            ".",
        ],
    ),
    _t(
        "tpl_bank_02",
        "fam_banking_in",
        "possible_exposure",
        [
            "Vendor payout details:\nBeneficiary: ",
            ("name", "PERSON"),
            "\nA/C No: ",
            ("account_number", "ACCOUNT_NUMBER"),
            "\nIFSC: ",
            ("ifsc", "None"),
        ],
    ),
    _t(
        "tpl_bank_03",
        "fam_banking_in",
        "possible_exposure",
        [
            "International wire remittance instructions: IBAN: ",
            ("iban", "IBAN"),
            " under account holder ",
            ("name", "PERSON"),
            ".",
        ],
    ),
    _t(
        "tpl_bank_04",
        "fam_banking_in",
        "possible_exposure",
        [
            "Bank account update request for employee ",
            ("name", "PERSON"),
            ": new account number is ",
            ("account_number", "ACCOUNT_NUMBER"),
            ".",
        ],
    ),
    _t(
        "tpl_bank_05",
        "fam_banking_in",
        "possible_exposure",
        [
            "IMPS transfer confirmation: INR 25,000 sent to A/C ",
            ("account_number", "ACCOUNT_NUMBER"),
            " (IFSC: ",
            ("ifsc", "None"),
            ").",
        ],
    ),
    _t(
        "tpl_bank_06",
        "fam_banking_in",
        "possible_exposure",
        [
            "Cross-border supplier payment: Wire funds to IBAN ",
            ("iban", "IBAN"),
            " for invoice settlement.",
        ],
    ),
    _t(
        "tpl_bank_07",
        "fam_banking_in",
        "possible_exposure",
        [
            "Direct deposit enrollment form: Employee: ",
            ("name", "PERSON"),
            ", Bank A/C: ",
            ("account_number", "ACCOUNT_NUMBER"),
            ", Email: ",
            ("email", "EMAIL"),
            ".",
        ],
    ),
    _t(
        "tpl_bank_08",
        "fam_banking_in",
        "possible_exposure",
        [
            "Dividend payout dispatch to account ",
            ("account_number", "ACCOUNT_NUMBER"),
            " held by ",
            ("name", "PERSON"),
            ".",
        ],
    ),
    _t(
        "tpl_bank_09",
        "fam_banking_in",
        "possible_exposure",
        [
            "Supplier bank verification:\nCompany Rep: ",
            ("name", "PERSON"),
            "\nBank Account: ",
            ("account_number", "ACCOUNT_NUMBER"),
            "\nContact Phone: ",
            ("phone", "PHONE"),
        ],
    ),
    _t(
        "tpl_bank_10",
        "fam_banking_in",
        "possible_exposure",
        [
            "Transfer failed: Invalid IFSC code for account ",
            ("account_number", "ACCOUNT_NUMBER"),
            ". Please verify with customer at ",
            ("email", "EMAIL"),
            ".",
        ],
    ),
    _t(
        "tpl_bank_11",
        "fam_banking_in",
        "possible_exposure",
        [
            "Banking mandate registered: Account: ",
            ("account_number", "ACCOUNT_NUMBER"),
            ", IFSC: ",
            ("ifsc", "None"),
            ", Holder: ",
            ("name", "PERSON"),
            ".",
        ],
    ),
]

# -----------------------------------------------------------------------------
# 8. fam_hr_recruitment (POSSIBLE EXPOSURE) - 10 templates
# -----------------------------------------------------------------------------
_FAM_HR_RECRUITMENT = [
    _t(
        "tpl_hr_01",
        "fam_hr_recruitment",
        "possible_exposure",
        [
            "Candidate profile for Senior Engineer role: Name: ",
            ("name", "PERSON"),
            ", Email: ",
            ("email", "EMAIL"),
            ", Mobile: ",
            ("phone", "PHONE"),
            ".",
        ],
    ),
    _t(
        "tpl_hr_02",
        "fam_hr_recruitment",
        "possible_exposure",
        [
            "Interview invitation sent to ",
            ("name", "PERSON"),
            " at ",
            ("email", "EMAIL"),
            " for round 2 technical review.",
        ],
    ),
    _t(
        "tpl_hr_03",
        "fam_hr_recruitment",
        "possible_exposure",
        [
            "HR Onboarding Checklist:\nFull Name: ",
            ("name", "PERSON"),
            "\nPersonal Email: ",
            ("email", "EMAIL"),
            "\nPhone Number: ",
            ("phone", "PHONE"),
        ],
    ),
    _t(
        "tpl_hr_04",
        "fam_hr_recruitment",
        "possible_exposure",
        [
            "Offer letter released for ",
            ("name", "PERSON"),
            ". Compensation details dispatched to ",
            ("email", "EMAIL"),
            ".",
        ],
    ),
    _t(
        "tpl_hr_05",
        "fam_hr_recruitment",
        "possible_exposure",
        [
            "Candidate reference check notes: Spoke with previous manager regarding ",
            ("name", "PERSON"),
            " (Phone: ",
            ("phone", "PHONE"),
            ").",
        ],
    ),
    _t(
        "tpl_hr_06",
        "fam_hr_recruitment",
        "possible_exposure",
        [
            "Talent pipeline update: Candidate ",
            ("name", "PERSON"),
            " accepted position. Contact at ",
            ("phone", "PHONE"),
            ".",
        ],
    ),
    _t(
        "tpl_hr_07",
        "fam_hr_recruitment",
        "possible_exposure",
        [
            "Employee directory update:\nName: ",
            ("name", "PERSON"),
            "\nEmail: ",
            ("email", "EMAIL"),
            "\nWork Mobile: ",
            ("phone", "PHONE"),
        ],
    ),
    _t(
        "tpl_hr_08",
        "fam_hr_recruitment",
        "possible_exposure",
        [
            "Background screening report received for applicant ",
            ("name", "PERSON"),
            ", contact verified via ",
            ("email", "EMAIL"),
            ".",
        ],
    ),
    _t(
        "tpl_hr_09",
        "fam_hr_recruitment",
        "possible_exposure",
        [
            "Campus recruitment shortlist: Student: ",
            ("name", "PERSON"),
            " | Contact: ",
            ("phone", "PHONE"),
            " | Email: ",
            ("email", "EMAIL"),
        ],
    ),
    _t(
        "tpl_hr_10",
        "fam_hr_recruitment",
        "possible_exposure",
        [
            "Contractor onboarding profile:\nVendor Specialist: ",
            ("name", "PERSON"),
            "\nDirect Phone: ",
            ("phone", "PHONE"),
            "\nEmail: ",
            ("email", "EMAIL"),
        ],
    ),
]

# -----------------------------------------------------------------------------
# 9. fam_customer_support (POSSIBLE EXPOSURE) - 10 templates
# -----------------------------------------------------------------------------
_FAM_CUSTOMER_SUPPORT = [
    _t(
        "tpl_supp_01",
        "fam_customer_support",
        "possible_exposure",
        [
            "Support Ticket #84920: Customer ",
            ("name", "PERSON"),
            " reported login issues. Reach them at ",
            ("email", "EMAIL"),
            " or ",
            ("phone", "PHONE"),
            ".",
        ],
    ),
    _t(
        "tpl_supp_02",
        "fam_customer_support",
        "possible_exposure",
        [
            "Refund inquiry from customer ",
            ("name", "PERSON"),
            " (phone: ",
            ("phone", "PHONE"),
            ") regarding disputed transaction.",
        ],
    ),
    _t(
        "tpl_supp_03",
        "fam_customer_support",
        "possible_exposure",
        [
            "Customer callback request:\nName: ",
            ("name", "PERSON"),
            "\nPhone: ",
            ("phone", "PHONE"),
            "\nEmail: ",
            ("email", "EMAIL"),
            "\nIssue: Service outage",
        ],
    ),
    _t(
        "tpl_supp_04",
        "fam_customer_support",
        "possible_exposure",
        [
            "Complaint escalation: User ",
            ("name", "PERSON"),
            " (",
            ("email", "EMAIL"),
            ") requested account manager contact.",
        ],
    ),
    _t(
        "tpl_supp_05",
        "fam_customer_support",
        "possible_exposure",
        [
            "CRM contact record created for ",
            ("name", "PERSON"),
            " with email ",
            ("email", "EMAIL"),
            " and mobile ",
            ("phone", "PHONE"),
            ".",
        ],
    ),
    _t(
        "tpl_supp_06",
        "fam_customer_support",
        "possible_exposure",
        [
            "Billing dispute resolved for client ",
            ("name", "PERSON"),
            ". Confirmation sent to ",
            ("email", "EMAIL"),
            ".",
        ],
    ),
    _t(
        "tpl_supp_07",
        "fam_customer_support",
        "possible_exposure",
        [
            "Follow-up scheduled with client ",
            ("name", "PERSON"),
            " at phone ",
            ("phone", "PHONE"),
            " regarding system setup.",
        ],
    ),
    _t(
        "tpl_supp_08",
        "fam_customer_support",
        "possible_exposure",
        [
            "Support chat transcript: Client ",
            ("name", "PERSON"),
            " (",
            ("phone", "PHONE"),
            ") requested password reset assistance.",
        ],
    ),
    _t(
        "tpl_supp_09",
        "fam_customer_support",
        "possible_exposure",
        [
            "Customer satisfaction survey dispatched to ",
            ("email", "EMAIL"),
            " for respondent ",
            ("name", "PERSON"),
            ".",
        ],
    ),
    _t(
        "tpl_supp_10",
        "fam_customer_support",
        "possible_exposure",
        [
            "VIP customer contact card:\nClient: ",
            ("name", "PERSON"),
            "\nDirect: ",
            ("phone", "PHONE"),
            "\nEmail: ",
            ("email", "EMAIL"),
        ],
    ),
]

# -----------------------------------------------------------------------------
# 10. fam_multiline_tickets (POSSIBLE EXPOSURE) - 10 templates
# -----------------------------------------------------------------------------
_FAM_MULTILINE = [
    _t(
        "tpl_multi_01",
        "fam_multiline_tickets",
        "possible_exposure",
        [
            "INCIDENT HANDOVER NOTE\nDate: 2026-10-18\nEngineer On Duty: ",
            ("name", "PERSON"),
            "\nEscalation Contact: ",
            ("phone", "PHONE"),
            "\nStatus: Mitigated\nNext steps: Monitor DB load.",
        ],
    ),
    _t(
        "tpl_multi_02",
        "fam_multiline_tickets",
        "possible_exposure",
        [
            "CLIENT INTAKE SUMMARY\n---------------------\nClient Name: ",
            ("name", "PERSON"),
            "\nOfficial Email: ",
            ("email", "EMAIL"),
            "\nContact: ",
            ("phone", "PHONE"),
            "\nRequirement: Data migration audit.",
        ],
    ),
    _t(
        "tpl_multi_03",
        "fam_multiline_tickets",
        "possible_exposure",
        [
            "MEETING MINUTES\nAttendees: Dev team lead, QA specialist\nReporter: ",
            ("name", "PERSON"),
            "\nAction Item: Send spec to ",
            ("email", "EMAIL"),
            " by EOD Friday.",
        ],
    ),
    _t(
        "tpl_multi_04",
        "fam_multiline_tickets",
        "possible_exposure",
        [
            "VENDOR SERVICE AGREEMENT\nCounterparty: Apex Tech Solutions\nPrimary Representative: ",
            ("name", "PERSON"),
            "\nDirect Line: ",
            ("phone", "PHONE"),
            "\nEmail Address: ",
            ("email", "EMAIL"),
        ],
    ),
    _t(
        "tpl_multi_05",
        "fam_multiline_tickets",
        "possible_exposure",
        [
            "SECURITY ACCESS REQUEST\nUser ID: USR-9021\nEmployee Name: ",
            ("name", "PERSON"),
            "\nApproval Manager Email: ",
            ("email", "EMAIL"),
            "\nDesk Ext: ",
            ("phone", "PHONE"),
        ],
    ),
    _t(
        "tpl_multi_06",
        "fam_multiline_tickets",
        "possible_exposure",
        [
            "PROJECT STATUS BRIEFING\nSprint: 42\nScrum Master: ",
            ("name", "PERSON"),
            "\nReach out via ",
            ("phone", "PHONE"),
            " for blocker clearance.",
        ],
    ),
    _t(
        "tpl_multi_07",
        "fam_multiline_tickets",
        "possible_exposure",
        [
            "AUDIT LOG ENTRY\nSubject: User Access Review\nReviewed By: ",
            ("name", "PERSON"),
            "\nReviewer Contact: ",
            ("email", "EMAIL"),
            "\nFindings: No anomalies detected.",
        ],
    ),
    _t(
        "tpl_multi_08",
        "fam_multiline_tickets",
        "possible_exposure",
        [
            "CUSTOMER ESCALATION NOTE\nCustomer: ",
            ("name", "PERSON"),
            "\nRegistered Phone: ",
            ("phone", "PHONE"),
            "\nEmail: ",
            ("email", "EMAIL"),
            "\nPriority: P1 - Critical.",
        ],
    ),
    _t(
        "tpl_multi_09",
        "fam_multiline_tickets",
        "possible_exposure",
        [
            "SHIFT HANDOVER\nIncoming Lead: ",
            ("name", "PERSON"),
            "\nEmergency Phone: ",
            ("phone", "PHONE"),
            "\nNotes: All batch jobs completed successfully.",
        ],
    ),
    _t(
        "tpl_multi_10",
        "fam_multiline_tickets",
        "possible_exposure",
        [
            "FACILITY VISIT APPROVAL\nVisitor: ",
            ("name", "PERSON"),
            "\nHost Email: ",
            ("email", "EMAIL"),
            "\nContact Mobile: ",
            ("phone", "PHONE"),
            "\nGate Pass: Approved.",
        ],
    ),
]

# -----------------------------------------------------------------------------
# 11. fam_decoy_negative (NO EXPOSURE) - 12 templates
# -----------------------------------------------------------------------------
_FAM_DECOY = [
    _t(
        "tpl_decoy_01",
        "fam_decoy_negative",
        "no_exposure",
        [
            'To configure your local environment, set export API_KEY="',
            ("decoy_placeholder", None),
            '" in your shell profile.',
        ],
    ),
    _t(
        "tpl_decoy_02",
        "fam_decoy_negative",
        "no_exposure",
        [
            "For technical documentation questions, contact ",
            ("decoy_email", None),
            " or refer to the developer portal guide.",
        ],
    ),
    _t(
        "tpl_decoy_03",
        "fam_decoy_negative",
        "no_exposure",
        [
            "Package shipment confirmed. Tracking number: ",
            ("decoy_order_id", None),
            ". Estimated arrival in 2 business days.",
        ],
    ),
    _t(
        "tpl_decoy_04",
        "fam_decoy_negative",
        "no_exposure",
        [
            "Released update ",
            ("decoy_version", None),
            " addressing dependency vulnerability CVE-2026-9921.",
        ],
    ),
    _t(
        "tpl_decoy_05",
        "fam_decoy_negative",
        "no_exposure",
        [
            "Test transaction failed with mock non-card sequence: ",
            ("decoy_card_number", None),
            " (expected Luhn rejection).",
        ],
    ),
    _t(
        "tpl_decoy_06",
        "fam_decoy_negative",
        "no_exposure",
        [
            "Invalid UIDAI format test: string ",
            ("decoy_aadhaar", None),
            " was properly discarded by the input sanitizer.",
        ],
    ),
    _t(
        "tpl_decoy_07",
        "fam_decoy_negative",
        "no_exposure",
        [
            "Sample tax ID decoy string: ",
            ("decoy_pan", None),
            " does not match statutory alphanumeric regex.",
        ],
    ),
    _t(
        "tpl_decoy_08",
        "fam_decoy_negative",
        "no_exposure",
        [
            "Please replace `<INSERT_PASSWORD_HERE>` with your personal passphrase when initializing vault."
        ],
    ),
    _t(
        "tpl_decoy_09",
        "fam_decoy_negative",
        "no_exposure",
        [
            "API documentation sample: `curl -H 'Authorization: Bearer <TOKEN>' https://api.example.com/v1/health`"
        ],
    ),
    _t(
        "tpl_decoy_10",
        "fam_decoy_negative",
        "no_exposure",
        [
            "Order invoice reference: ",
            ("decoy_order_id", None),
            " generated for automated build testing on version ",
            ("decoy_version", None),
            ".",
        ],
    ),
    _t(
        "tpl_decoy_11",
        "fam_decoy_negative",
        "no_exposure",
        [
            "Mock user account created: support@",
            ("decoy_placeholder", None),
            ".domain with password placeholder `YOUR_PASSWORD`.",
        ],
    ),
    _t(
        "tpl_decoy_12",
        "fam_decoy_negative",
        "no_exposure",
        [
            "Testing negative filter: Contact address info@example.org and tracking code ",
            ("decoy_order_id", None),
            ".",
        ],
    ),
]

# -----------------------------------------------------------------------------
# 12. fam_ecommerce_orders (NO EXPOSURE) - 10 templates
# -----------------------------------------------------------------------------
_FAM_ECOMMERCE = [
    _t(
        "tpl_ecom_01",
        "fam_ecommerce_orders",
        "no_exposure",
        [
            "Your order ",
            ("decoy_order_id", None),
            " has been dispatched via standard ground freight.",
        ],
    ),
    _t(
        "tpl_ecom_02",
        "fam_ecommerce_orders",
        "no_exposure",
        [
            "Invoice receipt for transaction ",
            ("decoy_order_id", None),
            ": Total amount $42.50 USD. Thank you for your business!",
        ],
    ),
    _t(
        "tpl_ecom_03",
        "fam_ecommerce_orders",
        "no_exposure",
        [
            "Warehouse inventory report: Restocked 250 units under SKU-",
            ("decoy_order_id", None),
            ".",
        ],
    ),
    _t(
        "tpl_ecom_04",
        "fam_ecommerce_orders",
        "no_exposure",
        [
            "Return merchandise authorization approved. Please label package with RMA: ",
            ("decoy_order_id", None),
            ".",
        ],
    ),
    _t(
        "tpl_ecom_05",
        "fam_ecommerce_orders",
        "no_exposure",
        [
            "Delivery rescheduled for tracking number ",
            ("decoy_order_id", None),
            " per customer delivery instructions.",
        ],
    ),
    _t(
        "tpl_ecom_06",
        "fam_ecommerce_orders",
        "no_exposure",
        [
            "Cart checkout abandoned: Session ID ",
            ("decoy_order_id", None),
            " saved for automatic cart recovery.",
        ],
    ),
    _t(
        "tpl_ecom_07",
        "fam_ecommerce_orders",
        "no_exposure",
        [
            "Purchase requisition PR-",
            ("decoy_order_id", None),
            " submitted to procurement committee for sign-off.",
        ],
    ),
    _t(
        "tpl_ecom_08",
        "fam_ecommerce_orders",
        "no_exposure",
        ["Shipping manifest entry: Container C-409, Manifest ID ", ("decoy_order_id", None), "."],
    ),
    _t(
        "tpl_ecom_09",
        "fam_ecommerce_orders",
        "no_exposure",
        [
            "Store credit voucher code VOUCH-",
            ("decoy_order_id", None),
            " credited to digital wallet.",
        ],
    ),
    _t(
        "tpl_ecom_10",
        "fam_ecommerce_orders",
        "no_exposure",
        [
            "Order cancellation confirmed for order ",
            ("decoy_order_id", None),
            ". No funds were debited.",
        ],
    ),
]

# -----------------------------------------------------------------------------
# 13. fam_policy_guidance (NO EXPOSURE) - 10 templates
# -----------------------------------------------------------------------------
_FAM_POLICY = [
    _t(
        "tpl_pol_01",
        "fam_policy_guidance",
        "no_exposure",
        [
            "Corporate Password Policy: Passwords must contain at least 14 characters, numbers, and symbols."
        ],
    ),
    _t(
        "tpl_pol_02",
        "fam_policy_guidance",
        "no_exposure",
        [
            "Reminder: Never paste production secrets, database credentials, or API tokens into public channels."
        ],
    ),
    _t(
        "tpl_pol_03",
        "fam_policy_guidance",
        "no_exposure",
        [
            "Security awareness training module 3 must be completed by all software engineering staff by Friday."
        ],
    ),
    _t(
        "tpl_pol_04",
        "fam_policy_guidance",
        "no_exposure",
        [
            "All customer data exports must be sanitized and encrypted in accordance with GDPR and DPDP compliance."
        ],
    ),
    _t(
        "tpl_pol_05",
        "fam_policy_guidance",
        "no_exposure",
        [
            "Multi-factor authentication (MFA) is mandatory for all Google Workspace and GitHub developer accounts."
        ],
    ),
    _t(
        "tpl_pol_06",
        "fam_policy_guidance",
        "no_exposure",
        [
            "Weekly engineering standup will be hosted on Google Meet at 10:00 AM IST. Agenda: Sprint retrospective."
        ],
    ),
    _t(
        "tpl_pol_07",
        "fam_policy_guidance",
        "no_exposure",
        [
            "System maintenance window: Core network routers will undergo scheduled firmware upgrades this Sunday."
        ],
    ),
    _t(
        "tpl_pol_08",
        "fam_policy_guidance",
        "no_exposure",
        [
            "Data classification standard: Confidential information must not be stored on local unencrypted drives."
        ],
    ),
    _t(
        "tpl_pol_09",
        "fam_policy_guidance",
        "no_exposure",
        [
            "Incident response protocol: Immediately alert security-operations in the event of suspected credentials leak."
        ],
    ),
    _t(
        "tpl_pol_10",
        "fam_policy_guidance",
        "no_exposure",
        ["Clean desk policy: Lock your workstation whenever stepping away from your workspace."],
    ),
]

# -----------------------------------------------------------------------------
# 14. fam_unicode_samples (MIXED LABELS) - 10 templates
# -----------------------------------------------------------------------------
_FAM_UNICODE = [
    _t(
        "tpl_uni_01",
        "fam_unicode_samples",
        "possible_exposure",
        [
            "नमस्ते! ग्राहक संपर्क विवरण: नाम: ",
            ("name", "PERSON"),
            ", ईमेल: ",
            ("email", "EMAIL"),
            ", फ़ोन: ",
            ("phone", "PHONE"),
            "। धन्यवाद!",
        ],
    ),
    _t(
        "tpl_uni_02",
        "fam_unicode_samples",
        "high_risk_exposure",
        [
            "🚨 Security Alert: Production API key leaked in chat! Key: ",
            ("api_key", "API_KEY"),
            " ⚠️ Please revoke immediately!",
        ],
    ),
    _t(
        "tpl_uni_03",
        "fam_unicode_samples",
        "possible_exposure",
        [
            "வணக்கம்! உங்கள் வங்கி கணக்கு எண்: ",
            ("account_number", "ACCOUNT_NUMBER"),
            ", IFSC: ",
            ("ifsc", "None"),
            ", பெயர்: ",
            ("name", "PERSON"),
            ".",
        ],
    ),
    _t(
        "tpl_uni_04",
        "fam_unicode_samples",
        "no_exposure",
        [
            "🎉 Congratulations team on successfully releasing version ",
            ("decoy_version", None),
            "! Great work everyone 🚀👏",
        ],
    ),
    _t(
        "tpl_uni_05",
        "fam_unicode_samples",
        "high_risk_exposure",
        [
            "⚠️ Urgent: DB password compromised: `",
            ("password", "PASSWORD"),
            "` 🔒 Please rotate credentials.",
        ],
    ),
    _t(
        "tpl_uni_06",
        "fam_unicode_samples",
        "possible_exposure",
        [
            "Kyc सत्यापन पूर्ण: आधार संख्या ",
            ("aadhaar", "AADHAAR"),
            " एवं पैन संख्या ",
            ("pan", "PAN"),
            "। स्थिति: स्वीकृत ✅",
        ],
    ),
    _t(
        "tpl_uni_07",
        "fam_unicode_samples",
        "no_exposure",
        ["📦 पार्सल ट्रैकिंग संख्या: ", ("decoy_order_id", None), "। डिलीवरी कल अपेक्षित है।"],
    ),
    _t(
        "tpl_uni_08",
        "fam_unicode_samples",
        "high_risk_exposure",
        [
            "💳 Payment test receipt: Card: ",
            ("card_number", "CARD"),
            " | Status: Confirmed ✅ | Amt: ₹9,999",
        ],
    ),
    _t(
        "tpl_uni_09",
        "fam_unicode_samples",
        "possible_exposure",
        [
            "Candidate CV screening 📄: Candidate ",
            ("name", "PERSON"),
            " (📧 ",
            ("email", "EMAIL"),
            ", 📱 ",
            ("phone", "PHONE"),
            ").",
        ],
    ),
    _t(
        "tpl_uni_10",
        "fam_unicode_samples",
        "no_exposure",
        ["💡 Tip: Use `chmod 600 ~/.ssh/id_rsa` to protect your local private keys 🔑."],
    ),
]

# -----------------------------------------------------------------------------
# 15. fam_casing_variants (MIXED LABELS) - 10 templates
# -----------------------------------------------------------------------------
_FAM_CASING = [
    _t(
        "tpl_case_01",
        "fam_casing_variants",
        "high_risk_exposure",
        [
            "CRITICAL LEAK: URGENTLY REVOKE AWS ACCESS KEY ID: ",
            ("api_key", "API_KEY"),
            " FOUND IN PUBLIC REPOSITORY!",
        ],
    ),
    _t(
        "tpl_case_02",
        "fam_casing_variants",
        "possible_exposure",
        [
            "hey pls find contact for candidate ",
            ("name", "PERSON"),
            " mail is ",
            ("email", "EMAIL"),
            " and cell ",
            ("phone", "PHONE"),
            " thx",
        ],
    ),
    _t(
        "tpl_case_03",
        "fam_casing_variants",
        "high_risk_exposure",
        [
            "yo i forgot staging pass again.. is it still ",
            ("password", "PASSWORD"),
            " ?? let me know asap",
        ],
    ),
    _t(
        "tpl_case_04",
        "fam_casing_variants",
        "no_exposure",
        ["HEY TEAM PLEASE REMEMBER STANDUP IS AT 10:00 AM SHARP TODAY IN ROOM B."],
    ),
    _t(
        "tpl_case_05",
        "fam_casing_variants",
        "possible_exposure",
        [
            "CONFIDENTIAL KYC FILE: PAN NUMBER: ",
            ("pan", "PAN"),
            " HOLDER: ",
            ("name", "PERSON"),
            ".",
        ],
    ),
    _t(
        "tpl_case_06",
        "fam_casing_variants",
        "high_risk_exposure",
        [
            "error log dump:\nCREDENTIALS EXPOSED: USER=",
            ("email", "EMAIL"),
            " PASSWORD=",
            ("password", "PASSWORD"),
        ],
    ),
    _t(
        "tpl_case_07",
        "fam_casing_variants",
        "no_exposure",
        ["order tracking update: ref no ", ("decoy_order_id", None), " has been shipped."],
    ),
    _t(
        "tpl_case_08",
        "fam_casing_variants",
        "possible_exposure",
        [
            "payout wire details: beneficiary ",
            ("name", "PERSON"),
            " acct num ",
            ("account_number", "ACCOUNT_NUMBER"),
            " ifsc ",
            ("ifsc", "None"),
        ],
    ),
    _t(
        "tpl_case_09",
        "fam_casing_variants",
        "high_risk_exposure",
        ["CHARGE LOG: VISA ", ("card_number", "CARD"), " BILLED TO ", ("name", "PERSON")],
    ),
    _t(
        "tpl_case_10",
        "fam_casing_variants",
        "no_exposure",
        ["reminder: documentation available at https://docs.example.com for all api references."],
    ),
]

ALL_TEMPLATES: list[Template] = (
    _FAM_CLOUD_INFRA
    + _FAM_CRED_CHAT
    + _FAM_CRED_GIT
    + _FAM_FIN_CARDS
    + _FAM_DEV_LOGS
    + _FAM_IDENTITY_IN
    + _FAM_BANKING_IN
    + _FAM_HR_RECRUITMENT
    + _FAM_CUSTOMER_SUPPORT
    + _FAM_MULTILINE
    + _FAM_DECOY
    + _FAM_ECOMMERCE
    + _FAM_POLICY
    + _FAM_UNICODE
    + _FAM_CASING
)

# Family ID mapping for convenience
FAMILY_MAP = {}
for tpl in ALL_TEMPLATES:
    FAMILY_MAP.setdefault(tpl.family_id, []).append(tpl)
