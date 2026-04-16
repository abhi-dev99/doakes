"""
ARGUS Survey Auto-Submitter  —  300 unique respondents
=======================================================
Generates and POSTs 300 realistic, varied survey responses.
Each respondent has a unique name, organisation, role, and opinion
shaped by their persona archetype.

Usage:
    python simulate_survey.py
    python simulate_survey.py --url http://localhost:8000
    python simulate_survey.py --delay 0.05 --count 300
"""

import argparse
import json
import random
import time
import urllib.request
import urllib.error

# ─────────────────────────────────────────────────────────────────────────────
# Name pools  (Indian names, diverse regions)
# ─────────────────────────────────────────────────────────────────────────────

FIRST_NAMES = [
    "Aarav","Abhi","Abhijeet","Abhilash","Abhimanyu","Abhishek","Aditya","Ajay","Ajit","Akash",
    "Alok","Amit","Amitabh","Amol","Ananya","Aniket","Anil","Anirban","Anish","Anita",
    "Anjali","Ankita","Anshul","Anuj","Anupam","Anupama","Anurag","Apoorv","Archana","Arjun",
    "Arnav","Arun","Aruna","Arvind","Ashish","Ashok","Ashutosh","Astha","Avani","Ayesha",
    "Ayush","Bharat","Bhavin","Deepa","Deepak","Deepika","Dev","Devika","Dhruv","Disha",
    "Divya","Gaurav","Gautam","Girish","Gopal","Hardik","Harish","Harsha","Hemant","Hiral",
    "Ishaan","Ishita","Jagdish","Jai","Jatin","Jay","Jayesh","Jyoti","Karan","Karthik",
    "Kavita","Kedar","Kishore","Komal","Krishna","Kunal","Lakshmi","Lalit","Lata","Madhav",
    "Manish","Manisha","Manoj","Meera","Mihir","Minal","Mohan","Mohit","Mridul","Mukesh",
    "Namrata","Nandini","Naresh","Natasha","Naveen","Neha","Nikhil","Nilesh","Niraj","Nisha",
    "Nishant","Nitesh","Nitin","Omkar","Parag","Parth","Pawan","Pooja","Prachi","Pradip",
    "Praful","Prashant","Pratik","Pravin","Preet","Preeti","Preethi","Priya","Priyanka","Puja",
    "Rahul","Raj","Rajat","Rajesh","Rajiv","Rakesh","Ramesh","Rashmi","Ravi","Rekha",
    "Ritesh","Ritu","Rohit","Roshan","Rucha","Rupesh","Sachin","Sahil","Sameer","Sandeep",
    "Sandesh","Sanjay","Sanjeev","Sanjiv","Santosh","Saurabh","Shailesh","Shantanu","Sharad","Shikha",
    "Shilpa","Shivam","Shreya","Shrey","Shruti","Shubham","Smita","Sneha","Soham","Sonal",
    "Sourabh","Subhash","Sudhir","Sujata","Sunil","Sunita","Suresh","Sushant","Swati","Tanmay",
    "Tanvi","Tejas","Tushar","Uday","Ujjwal","Umesh","Vaibhav","Varun","Vidya","Vijay",
    "Vikas","Vikram","Vinay","Vineet","Vishal","Vivek","Yash","Yogesh","Zara","Zoya"
]

LAST_NAMES = [
    "Agarwal","Ahuja","Bajaj","Banerjee","Bapat","Basu","Bhatt","Bose","Chakraborty","Chandra",
    "Chatterjee","Chauhan","Chopra","Das","Dave","Desai","Deshpande","Dey","Dubey","Dutta",
    "Garg","Ghosh","Gokhale","Goyal","Gupta","Iyer","Jain","Jha","Joshi","Kadam",
    "Kapoor","Kapur","Kashyap","Khanna","Khatri","Kulkarni","Kumar","Lal","Mane","Mehta",
    "Mishra","Mistry","Modi","Murthy","Nair","Naik","Pandey","Patel","Patil","Pawar",
    "Pillai","Prasad","Rao","Reddy","Roy","Sahoo","Sahu","Saxena","Sen","Shah",
    "Sharma","Shastri","Shinde","Shrivastava","Singh","Sinha","Srivastava","Thakur","Tiwari",
    "Trivedi","Varma","Verma","Yadav","Nanda","Malhotra","Bhattacharya","Menon","Krishnan","Rajan"
]

# ─────────────────────────────────────────────────────────────────────────────
# Organisation pools by type
# ─────────────────────────────────────────────────────────────────────────────

ORGS = {
    "Private Sector Bank": [
        "HDFC Bank Ltd.","ICICI Bank Ltd.","Axis Bank Ltd.","Kotak Mahindra Bank",
        "IndusInd Bank","Yes Bank Ltd.","Federal Bank Ltd.","IDFC FIRST Bank",
        "RBL Bank Ltd.","Bandhan Bank","South Indian Bank","Karnataka Bank",
        "City Union Bank","DCB Bank Ltd.","Karur Vysya Bank"
    ],
    "Public Sector Bank": [
        "State Bank of India","Bank of Baroda","Punjab National Bank",
        "Canara Bank","Union Bank of India","Bank of India","Central Bank of India",
        "Indian Bank","UCO Bank","Bank of Maharashtra","Punjab & Sind Bank",
        "Indian Overseas Bank"
    ],
    "Payment Service Provider (PSP)": [
        "Razorpay Software Pvt. Ltd.","PayU India Pvt. Ltd.","Cashfree Payments",
        "Instamojo Technologies","CCAvenue (Infibeam Avenues)","BillDesk",
        "PhonePe Payments Services","Google Pay India","Amazon Pay India",
        "Paytm Payments Bank","MobiKwik Systems","Freecharge (Axis Bank)"
    ],
    "Fintech / Neo-bank": [
        "Niyo Solutions Inc.","Jupiter Money","Fi Money (EpiFi Technologies)",
        "Slice (North East Small Finance Bank)","Groww (Nextbillion Technology)",
        "Zepto Financial Services","KreditBee (Krazybee Services)",
        "MoneyTap (Bhanix Finance)","Navi Technologies","OneCard (FPL Technologies)",
        "Freo (MWYN Tech)","Stashfin (Stash Financial Services)",
        "Lend (Bajaj Finance Finserv)","Smallcase Technologies","INDmoney"
    ],
    "E-commerce Platform": [
        "Meesho Inc.","Flipkart Internet Pvt. Ltd.","Amazon Seller Services Pvt. Ltd.",
        "Myntra Designs Pvt. Ltd.","Nykaa (FSN E-Commerce Ventures)",
        "BigBasket (Supermarket Grocery Supplies)","Swiggy (Bundl Technologies)",
        "Zomato Ltd.","Ola (ANI Technologies)","Urban Company",
        "Lenskart Solutions","Pepperfry Pvt. Ltd."
    ],
    "Government / DBT Platform": [
        "National Payments Corporation of India (NPCI)","NSDL e-Governance Infrastructure Ltd.",
        "Department of Financial Services, MoF","PMJDY Implementation Cell",
        "Reserve Bank Information Technology Pvt. Ltd. (ReBIT)","UIDAI",
        "Ministry of Electronics and IT (MeitY)","India Post Payments Bank",
        "Bharat BillPay (NBBL)","NeSL (National e-Governance Services Ltd.)"
    ],
    "Insurance / NBFC": [
        "Bajaj Finance Limited","Mahindra Finance","Muthoot Finance",
        "HDFC Life Insurance","ICICI Prudential Life Insurance",
        "SBI Life Insurance","LIC Digital","Star Health Insurance",
        "PolicyBazaar (PB Fintech)","Acko General Insurance"
    ]
}

EMAIL_DOMAINS = {
    "Private Sector Bank":              ["bank.co.in","corp.in","hq.in"],
    "Public Sector Bank":               ["bank.in","co.in","hq.co.in"],
    "Payment Service Provider (PSP)":   ["payments.in","tech.in","corp.com"],
    "Fintech / Neo-bank":               ["fintech.in","co","app.in"],
    "E-commerce Platform":              ["corp.in","tech.in","company.in"],
    "Government / DBT Platform":        ["gov.in","nic.in","org.in"],
    "Insurance / NBFC":                 ["insurance.in","finance.in","co.in"]
}

ROLES = [
    "Fraud Analyst","Risk Manager","CTO / Technology Head","Product Manager",
    "Compliance Officer","Software Engineer / Developer","Data Scientist / ML Engineer",
    "Business Analyst","C-Suite Executive","Other"
]

CURRENT_APPROACHES = [
    "Rule-based only","Basic ML model","Advanced ML / AI platform",
    "Third-party vendor solution","No automated detection currently"
]

TXN_VOLUMES = [
    "Under 10,000","10,000 \u2013 1 Lakh","1 Lakh \u2013 10 Lakh",
    "10 Lakh \u2013 1 Crore","Over 1 Crore"
]

LATENCY_OPTIONS = [
    "Under 5ms (real-time, no friction)",
    "Under 20ms (acceptable for UPI flow)",
    "Under 100ms (tolerable delay)",
    "Under 500ms (user barely notices)",
    "No strict requirement"
]

TRADEOFF_OPTIONS = [
    "Accuracy is everything \u2013 take as long as needed",
    "Prefer accuracy but speed matters",
    "Balanced \u2013 equal weight",
    "Prefer speed but accuracy matters",
    "Speed is critical \u2013 minimal latency overhead"
]

UPTIME_OPTIONS = [
    "99.9% (8.7 hrs downtime/year)",
    "99.95% (4.4 hrs downtime/year)",
    "99.99% (52 mins downtime/year)",
    "99.999% (5 mins downtime/year)",
    "No strict requirement"
]

TPS_OPTIONS = [
    "Under 100 TPS","100 \u2013 1,000 TPS","1,000 \u2013 10,000 TPS",
    "10,000 \u2013 1,00,000 TPS","Over 1,00,000 TPS"
]

DEPLOYMENT_OPTIONS = [
    "On-premises (own data centre)","Private cloud (dedicated)",
    "Public cloud \u2013 AWS / Azure / GCP","Hybrid (on-prem + cloud)",
    "SaaS / hosted by vendor"
]

ALL_FRAUD_TYPES   = ["digital_arrest","sim_swap","mule_account","upi_phishing",
                     "qr_fraud","account_takeover","card_fraud","money_laundering"]
ALL_INTEGRATIONS  = ["rest_api","websocket","kafka","sdk","webhook"]

# ─────────────────────────────────────────────────────────────────────────────
# Long-form open-text pools
# ─────────────────────────────────────────────────────────────────────────────

PAIN_POINTS = [
    "Our false positive rate is above 20%, leading to customer complaints and call centre overload. Legitimate transactions being blocked is eroding customer trust significantly.",
    "We have zero explainability in our current model. When auditors ask why a transaction was blocked, we cannot answer — this is a compliance nightmare.",
    "Post-transaction detection is useless for UPI — by the time fraud is flagged, the money is already in a mule account. We desperately need pre-authorization capability.",
    "Our rule-based engine hasn't been updated in 18 months. Fraudsters have adapted faster than our team can write rules. We need adaptive ML.",
    "We process over 50 lakh transactions daily with a team of 4 fraud analysts. Case volume is completely unmanageable without automated prioritisation.",
    "SIM swap attacks hit us hard last year — 3000+ customers affected. We have no device intelligence layer and our model doesn't detect device fingerprint changes.",
    "Digital arrest scams are a growing problem. Victims transfer large sums under police impersonation. We have no keyword detection for these conversation patterns.",
    "Merchant fraud on our platform is invisible to us. We can detect buyer-side fraud but have no risk profiling for the sellers/merchants who register with us.",
    "Graph-based fraud rings are our biggest gap. We know coordinated fraud happens but can't prove it or visualise the network — our current tools are completely flat.",
    "Regulatory reporting is manual and error-prone. Every quarter our compliance team spends 3 weeks manually compiling RBI MIS reports that should be automated.",
    "Our chargeback ratio has crossed the 1% threshold that card networks flag. We're at risk of losing merchant acquiring privileges if we don't bring it down fast.",
    "Latency is killing our conversion. Our existing fraud vendor adds 80ms to every checkout — that's a 4% conversion drop we can directly attribute to the fraud check.",
    "Mule accounts are our primary threat vector. We see dormant accounts activated, credited with large sums, and fully withdrawn within 48 hours.",
    "We have no velocity tracking across channels. A fraudster can hit our UPI, card, and wallets in parallel and our siloed systems don't see the combined pattern.",
    "Customer complaints about frozen accounts cost us 2 crore+ annually in relationship management. The legal team is under pressure to reduce preventive blocks.",
    "Our audit trail is incomplete — we store the decision but not the features that drove it. We cannot reconstruct why specific transactions were flagged months later.",
    "Multi-language fraud is a blind spot. We receive narrative remarks in Hindi and Marathi in transaction notes but our model only processes English tokens.",
    "Cross-border remittance monitoring is non-existent. We flag domestic patterns but miss hawala-style flows disguised as international remittances.",
    "Our current vendor's model is a black box SaaS. We have no ability to retrain it on our own customer base — the model is generic and not India-specific.",
    "Staff attrition in the fraud team means institutional knowledge about fraud patterns is being lost. We need a system that encodes pattern detection, not analyst intuition.",
    "3D Secure challenge rates are too high — we challenge 35% of transactions when the industry average is 8%. Most challenges are unnecessary friction.",
    "We onboarded a third-party fraud vendor 2 years ago but their model was trained on US data. India-specific patterns like digital arrest and UPI phishing are completely missed.",
    "Real-time alerting doesn't exist for us. Fraud is discovered during batch reconciliation, often 6-8 hours after the transactions occurred.",
    "QR code fraud is increasing sharply. Fake merchants register QR codes under impersonated business names and collect funds for weeks before detection.",
    "Device intelligence is primitive — we only check IP blacklists. A fraudster using a new SIM on a known device gets through without any challenge."
]

ADDITIONAL_REQS = [
    "Integration with our existing Finacle CBS ledger system via ISO 8583 messaging.",
    "Automated STR (Suspicious Transaction Report) generation for FIU-IND in prescribed XML schema.",
    "SDK library for embedding fraud scoring directly in our mobile app — cannot afford a network call for every transaction.",
    "Custom rule builder UI so our fraud operations team can define and deploy new rules without engineering involvement.",
    "DPDP Act (Digital Personal Data Protection) compliance documentation and data subject access request handling.",
    "Real-time chargeback dispute integration with Visa/Mastercard dispute resolution APIs.",
    "Aadhaar seeding validation to cross-check beneficiary identity against UIDAI records.",
    "Multi-region deployment with active-active failover across Mumbai and Hyderabad AWS regions.",
    "Native biometric challenge support — trigger fingerprint/FaceID via our existing mobile SDK rather than falling back to OTP.",
    "Push notification support for in-app fraud alerts with deep-link to case review screen.",
    "Federated learning capability so we can collaborate on fraud pattern detection with partner banks without sharing raw transaction data.",
    "Batch scoring API for overnight risk rescoring of the full customer portfolio — not just real-time transactions.",
    "Webhook-based alert delivery to PagerDuty for our on-call fraud response team.",
    "SIEM integration — forward fraud events to our existing Splunk deployment via syslog/CEF format.",
    "Per-merchant risk scoring API that our onboarding team can call before approving new merchant registrations.",
    "",
    "",
    "",
    "Model performance dashboard with precision/recall/F1 trends visible to our data science team.",
    "A/B testing framework so we can shadow-test new model versions against production without affecting customers."
]

COMMENTS = [
    "The pre-authorization paradigm is exactly what India's payment ecosystem needs. Our entire industry is still reactive.",
    "Would be keen to run a proof-of-concept on our live transaction stream — happy to share anonymised data.",
    "The graph-based fraud ring visualisation is a feature no competitor offers at this price point.",
    "Explainable AI is now a regulatory expectation from RBI, not just a nice-to-have. This positions ARGUS well.",
    "We've evaluated 4 fraud vendors this year — none of them had India-specific training data. Excited by ARGUS.",
    "The ensemble approach (XGBoost + Isolation Forest + LSTM) is the right architecture. Single models don't generalise.",
    "Would appreciate a mobile-responsive version of the analytics dashboard for on-call fraud analysts.",
    "Impressive scope for a prototype. The case management workflow alone is better than what we have in production.",
    "UPI fraud is an arms race — the threat intelligence update cadence (weekly) is critical to stay ahead.",
    "Concerned about model drift — want to understand the automated retraining pipeline in more detail.",
    "",
    "",
    "The mule account detection via graph centrality is particularly interesting for our PMGSY beneficiary fraud problem.",
    "We would pay a significant premium for the SIM swap detection feature alone — it's our #1 fraud vector right now.",
    "Real-time WebSocket dashboard would replace three separate tools our team currently uses.",
    "If the p50 latency claim of 5ms is validated in load testing, this is a game-changer for UPI payment flows.",
    "Happy to provide a letter of intent for a pilot deployment — please reach out to our CTO's office.",
    "The regulatory compliance section shows deep understanding of RBI/NPCI requirements. Rare to see in a product this early.",
]

# ─────────────────────────────────────────────────────────────────────────────
# Archetype bias tables
# ─────────────────────────────────────────────────────────────────────────────

ARCHETYPE_BIAS = {
    "Private Sector Bank": {
        "pre_auth": (4,5),"latency_idx": (0,1),"tradeoff_idx": (1,2),
        "explainability": (4,5),"india_specific": (4,5),
        "uptime_idx": (2,3),"tps_idx": (3,4),"residency": "India-only (strict)",
        "retention": "7 years (RBI mandate)","rto_idx": (1,2),
        "deployment_idx": (0,3),"scaling": "yes",
        "fraud_types_pool": ["digital_arrest","sim_swap","mule_account","upi_phishing","account_takeover","money_laundering"],
        "fraud_count": (4,6)
    },
    "Public Sector Bank": {
        "pre_auth": (3,5),"latency_idx": (1,3),"tradeoff_idx": (0,2),
        "explainability": (4,5),"india_specific": (5,5),
        "uptime_idx": (2,3),"tps_idx": (3,4),"residency": "India-only (strict)",
        "retention": "7 years (RBI mandate)","rto_idx": (1,3),
        "deployment_idx": (0,0),"scaling": "preferred",
        "fraud_types_pool": ["digital_arrest","mule_account","money_laundering","sim_swap","upi_phishing"],
        "fraud_count": (3,5)
    },
    "Payment Service Provider (PSP)": {
        "pre_auth": (5,5),"latency_idx": (0,0),"tradeoff_idx": (3,4),
        "explainability": (2,4),"india_specific": (3,4),
        "uptime_idx": (3,4),"tps_idx": (3,4),"residency": "India preferred, flexible if needed",
        "retention": "3 years","rto_idx": (0,1),
        "deployment_idx": (2,3),"scaling": "yes",
        "fraud_types_pool": ["upi_phishing","qr_fraud","account_takeover","card_fraud","sim_swap"],
        "fraud_count": (3,5)
    },
    "Fintech / Neo-bank": {
        "pre_auth": (4,5),"latency_idx": (0,1),"tradeoff_idx": (2,3),
        "explainability": (3,5),"india_specific": (3,4),
        "uptime_idx": (1,3),"tps_idx": (2,3),"residency": "India preferred, flexible if needed",
        "retention": "5 years","rto_idx": (1,2),
        "deployment_idx": (2,2),"scaling": "yes",
        "fraud_types_pool": ["sim_swap","account_takeover","upi_phishing","card_fraud"],
        "fraud_count": (2,4)
    },
    "E-commerce Platform": {
        "pre_auth": (4,5),"latency_idx": (1,2),"tradeoff_idx": (0,1),
        "explainability": (2,3),"india_specific": (2,3),
        "uptime_idx": (1,2),"tps_idx": (2,4),"residency": "No restriction",
        "retention": "3 years","rto_idx": (2,3),
        "deployment_idx": (2,3),"scaling": "yes",
        "fraud_types_pool": ["card_fraud","account_takeover","mule_account","money_laundering","qr_fraud"],
        "fraud_count": (2,4)
    },
    "Government / DBT Platform": {
        "pre_auth": (2,4),"latency_idx": (2,4),"tradeoff_idx": (0,0),
        "explainability": (5,5),"india_specific": (4,5),
        "uptime_idx": (1,2),"tps_idx": (1,2),"residency": "India-only (strict)",
        "retention": "10+ years","rto_idx": (2,4),
        "deployment_idx": (0,0),"scaling": "not required",
        "fraud_types_pool": ["mule_account","money_laundering","digital_arrest"],
        "fraud_count": (1,3)
    },
    "Insurance / NBFC": {
        "pre_auth": (3,4),"latency_idx": (1,3),"tradeoff_idx": (1,2),
        "explainability": (3,5),"india_specific": (3,4),
        "uptime_idx": (1,2),"tps_idx": (1,2),"residency": "India preferred, flexible if needed",
        "retention": "5 years","rto_idx": (1,3),
        "deployment_idx": (0,2),"scaling": "preferred",
        "fraud_types_pool": ["account_takeover","upi_phishing","sim_swap","card_fraud"],
        "fraud_count": (2,4)
    }
}

# FR base ratings [decision_engine, velocity, challenge, device, graph, xai, alerts, case_mgmt, compliance, merchant, dashboard]
FR_BIAS = {
    "Private Sector Bank":              [5,5,5,4,5,5,5,5,5,4,4],
    "Public Sector Bank":               [4,4,3,3,4,5,4,5,5,3,4],
    "Payment Service Provider (PSP)":   [5,5,4,5,4,3,4,3,4,5,5],
    "Fintech / Neo-bank":               [4,4,5,5,3,4,5,4,4,3,5],
    "E-commerce Platform":              [5,5,3,4,5,3,5,5,3,5,4],
    "Government / DBT Platform":        [3,4,2,3,5,5,3,4,5,2,4],
    "Insurance / NBFC":                 [4,3,3,3,3,4,4,4,4,3,3]
}


def make_email(first: str, last: str, org_type: str, rng: random.Random) -> str:
    domain = rng.choice(EMAIL_DOMAINS.get(org_type, ["corp.in"]))
    styles = [
        f"{first.lower()}.{last.lower()}@{domain}",
        f"{first[0].lower()}{last.lower()}@{domain}",
        f"{first.lower()}{last[0].lower()}@{domain}",
        f"{first.lower()}_{last.lower()}@{domain}",
    ]
    return rng.choice(styles)


def generate_persona(idx: int, used_names: set) -> dict:
    rng = random.Random(idx * 97 + 13)

    # Unique full name
    for attempt in range(300):
        first = rng.choice(FIRST_NAMES)
        last  = rng.choice(LAST_NAMES)
        full  = f"{first} {last}"
        if full not in used_names:
            used_names.add(full)
            break
    else:
        full = f"{first} {last} {idx}"
        used_names.add(full)

    org_type     = rng.choice(list(ORGS.keys()))
    organisation = rng.choice(ORGS[org_type])
    role         = rng.choice(ROLES)
    email        = make_email(first, last, org_type, rng)

    bias    = ARCHETYPE_BIAS[org_type]
    fr_base = FR_BIAS[org_type]

    fr_fields = [
        "fr_decision_engine","fr_velocity","fr_challenge","fr_device","fr_graph",
        "fr_xai","fr_alerts","fr_case_mgmt","fr_compliance","fr_merchant","fr_dashboard"
    ]
    fr_ratings = {
        f: max(1, min(5, fr_base[i] + rng.randint(-1, 1)))
        for i, f in enumerate(fr_fields)
    }

    pool        = bias["fraud_types_pool"]
    fraud_count = rng.randint(*bias["fraud_count"])
    fraud_types = rng.sample(pool, min(fraud_count, len(pool)))
    integration = rng.sample(ALL_INTEGRATIONS, rng.randint(1, 3))

    return {
        "name":         full,
        "email":        email,
        "organisation": organisation,
        "role":         role,
        "org_type":     org_type,
        "current_approach":  rng.choice(CURRENT_APPROACHES),
        "txn_volume":        rng.choice(TXN_VOLUMES),
        "pre_auth_importance":      rng.randint(*bias["pre_auth"]),
        "latency_tolerance":        LATENCY_OPTIONS[rng.randint(*bias["latency_idx"])],
        "accuracy_speed_tradeoff":  TRADEOFF_OPTIONS[rng.randint(*bias["tradeoff_idx"])],
        "explainability_importance":  rng.randint(*bias["explainability"]),
        "india_specific_importance":  rng.randint(*bias["india_specific"]),
        **fr_ratings,
        "nfr_uptime":         UPTIME_OPTIONS[rng.randint(*bias["uptime_idx"])],
        "nfr_tps":            TPS_OPTIONS[rng.randint(*bias["tps_idx"])],
        "nfr_data_residency": bias["residency"],
        "nfr_log_retention":  bias["retention"],
        "nfr_rto":            ["Under 5 minutes","Under 30 minutes","Under 2 hours","Under 24 hours","No strict requirement"][rng.randint(*bias["rto_idx"])],
        "fraud_types":        fraud_types,
        "multilang_importance": rng.randint(2, 5),
        "integration":        integration,
        "deployment_model":   DEPLOYMENT_OPTIONS[rng.randint(*bias["deployment_idx"])],
        "scaling_requirement": bias["scaling"],
        "pain_point":             rng.choice(PAIN_POINTS),
        "additional_requirements": rng.choice(ADDITIONAL_REQS),
        "comments":               rng.choice(COMMENTS),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Submission logic
# ─────────────────────────────────────────────────────────────────────────────

PERSONAS = [
    {
        # ── Persona 1: Senior fraud analyst at a large private bank ──────────
        "name": "Priya Mehra",
        "email": "priya.mehra@hdfcbank.co.in",
        "organisation": "HDFC Bank Ltd.",
        "role": "Fraud Analyst",
        "org_type": "Private Sector Bank",
        "current_approach": "Rule-based only",
        "txn_volume": "Over 1 Crore",

        # Core priorities
        "pre_auth_importance": 5,
        "latency_tolerance": "Under 20ms (acceptable for UPI flow)",
        "accuracy_speed_tradeoff": "Prefer accuracy but speed matters",
        "explainability_importance": 5,
        "india_specific_importance": 5,

        # Functional req ratings
        "fr_decision_engine": 5,
        "fr_velocity": 5,
        "fr_challenge": 5,
        "fr_device": 4,
        "fr_graph": 5,
        "fr_xai": 5,
        "fr_alerts": 5,
        "fr_case_mgmt": 5,
        "fr_compliance": 5,
        "fr_merchant": 4,
        "fr_dashboard": 4,

        # NFR
        "nfr_uptime": "99.99% (52 mins downtime/year)",
        "nfr_tps": "Over 1,00,000 TPS",
        "nfr_data_residency": "India-only (strict)",
        "nfr_log_retention": "7 years (RBI mandate)",
        "nfr_rto": "Under 30 minutes",

        # India-specific
        "fraud_types": ["digital_arrest", "sim_swap", "mule_account", "upi_phishing", "account_takeover"],
        "multilang_importance": 4,

        # Integration
        "integration": ["rest_api", "kafka", "webhook"],
        "deployment_model": "On-premises (own data centre)",
        "scaling_requirement": "yes",

        # Open feedback
        "pain_point": "Our current rule engine has a 23% false positive rate which is causing significant customer friction and call centre load. We need a system that understands behavioural context, not just static rules. Chargeback rates have increased by 18% this financial year.",
        "additional_requirements": "Integration with our existing Finacle CBS and ability to ingest RBI CIBIL fraud repository feeds. Also mandatory requirement for AES-256 encryption at rest for all PII fields.",
        "comments": "The pre-authorization approach is exactly what the industry needs. Most vendors still operate post-transaction. We would like to run a pilot evaluation of ARGUS against our existing vendor in Q2 FY26."
    },
    {
        # ── Persona 2: CTO at a Payment Service Provider ─────────────────────
        "name": "Rohan Kapoor",
        "email": "rohan.kapoor@razorpay.com",
        "organisation": "Razorpay Software Pvt. Ltd.",
        "role": "CTO / Technology Head",
        "org_type": "Payment Service Provider (PSP)",
        "current_approach": "Advanced ML / AI platform",
        "txn_volume": "10 Lakh – 1 Crore",

        "pre_auth_importance": 5,
        "latency_tolerance": "Under 5ms (real-time, no friction)",
        "accuracy_speed_tradeoff": "Speed is critical – minimal latency overhead",
        "explainability_importance": 3,
        "india_specific_importance": 4,

        "fr_decision_engine": 5,
        "fr_velocity": 5,
        "fr_challenge": 4,
        "fr_device": 5,
        "fr_graph": 4,
        "fr_xai": 3,
        "fr_alerts": 4,
        "fr_case_mgmt": 3,
        "fr_compliance": 4,
        "fr_merchant": 5,
        "fr_dashboard": 5,

        "nfr_uptime": "99.999% (5 mins downtime/year)",
        "nfr_tps": "10,000 – 1,00,000 TPS",
        "nfr_data_residency": "India preferred, flexible if needed",
        "nfr_log_retention": "3 years",
        "nfr_rto": "Under 5 minutes",

        "fraud_types": ["upi_phishing", "qr_fraud", "account_takeover", "card_fraud"],
        "multilang_importance": 3,

        "integration": ["rest_api", "websocket", "kafka"],
        "deployment_model": "Public cloud – AWS / Azure / GCP",
        "scaling_requirement": "yes",

        "pain_point": "Latency is our number one constraint. Any fraud check adding more than 10ms to checkout flow causes measurable conversion drop. Our current vendor's p99 latency is 47ms which is unacceptable. We need sub-5ms consistently.",
        "additional_requirements": "Redis-based velocity counters that we can share across our microservices, not just internal to the fraud engine. Also need a proper SDK so we can embed the scoring model directly in our checkout service.",
        "comments": "Merchant reputation scoring is a huge gap in the market. We process for 8 lakh+ merchants and currently have zero visibility into per-merchant fraud patterns. This feature alone would justify adoption."
    },
    {
        # ── Persona 3: Compliance Officer at public sector bank ───────────────
        "name": "Ananya Krishnan",
        "email": "a.krishnan@sbi.co.in",
        "organisation": "State Bank of India",
        "role": "Compliance Officer",
        "org_type": "Public Sector Bank",
        "current_approach": "Rule-based only",
        "txn_volume": "Over 1 Crore",

        "pre_auth_importance": 4,
        "latency_tolerance": "Under 100ms (tolerable delay)",
        "accuracy_speed_tradeoff": "Balanced – equal weight",
        "explainability_importance": 5,
        "india_specific_importance": 5,

        "fr_decision_engine": 4,
        "fr_velocity": 4,
        "fr_challenge": 3,
        "fr_device": 3,
        "fr_graph": 4,
        "fr_xai": 5,
        "fr_alerts": 4,
        "fr_case_mgmt": 5,
        "fr_compliance": 5,
        "fr_merchant": 3,
        "fr_dashboard": 4,

        "nfr_uptime": "99.99% (52 mins downtime/year)",
        "nfr_tps": "Over 1,00,000 TPS",
        "nfr_data_residency": "India-only (strict)",
        "nfr_log_retention": "7 years (RBI mandate)",
        "nfr_rto": "Under 30 minutes",

        "fraud_types": ["digital_arrest", "mule_account", "money_laundering", "sim_swap"],
        "multilang_importance": 5,

        "integration": ["rest_api", "webhook"],
        "deployment_model": "On-premises (own data centre)",
        "scaling_requirement": "preferred",

        "pain_point": "The biggest issue is audit trails. When RBI asks us to explain a fraud decision, we cannot do it. Our current system gives us a score with no rationale. Explainable AI is non-negotiable for regulatory compliance.",
        "additional_requirements": "Automated generation of Suspicious Transaction Reports (STR) for Financial Intelligence Unit India (FIU-IND) in the prescribed XML format. Also need DPDP Act compliance documentation for data subject requests.",
        "comments": "Digital arrest scam detection is critical for us. We have seen a 270% increase in such cases in the last 8 months. Keyword detection in Hindi and regional languages is a must—most scams happen in vernacular."
    },
    {
        # ── Persona 4: Product Manager at a Fintech / Neo-bank ───────────────
        "name": "Vikram Nair",
        "email": "vikram@niyo.co",
        "organisation": "Niyo Solutions Inc.",
        "role": "Product Manager",
        "org_type": "Fintech / Neo-bank",
        "current_approach": "Basic ML model",
        "txn_volume": "1 Lakh – 10 Lakh",

        "pre_auth_importance": 4,
        "latency_tolerance": "Under 20ms (acceptable for UPI flow)",
        "accuracy_speed_tradeoff": "Prefer speed but accuracy matters",
        "explainability_importance": 4,
        "india_specific_importance": 4,

        "fr_decision_engine": 4,
        "fr_velocity": 4,
        "fr_challenge": 5,
        "fr_device": 5,
        "fr_graph": 3,
        "fr_xai": 4,
        "fr_alerts": 5,
        "fr_case_mgmt": 4,
        "fr_compliance": 4,
        "fr_merchant": 3,
        "fr_dashboard": 5,

        "nfr_uptime": "99.95% (4.4 hrs downtime/year)",
        "nfr_tps": "1,000 – 10,000 TPS",
        "nfr_data_residency": "India preferred, flexible if needed",
        "nfr_log_retention": "5 years",
        "nfr_rto": "Under 30 minutes",

        "fraud_types": ["sim_swap", "account_takeover", "upi_phishing", "card_fraud"],
        "multilang_importance": 3,

        "integration": ["rest_api", "websocket", "sdk"],
        "deployment_model": "Public cloud – AWS / Azure / GCP",
        "scaling_requirement": "yes",

        "pain_point": "We are a mobile-first company and device intelligence is critical for us. When a user's SIM is swapped, we need to detect it before they transact. Our current model only looks at transaction data and completely misses device context.",
        "additional_requirements": "Push notification integration for in-app fraud alerts. Also biometric challenge support since our app already has fingerprint and face ID—we want ARGUS to trigger these natively rather than falling back to OTP.",
        "comments": "The real-time dashboard looks promising for our fraud operations team. Would love to see a mobile-responsive version for on-call analysts."
    },
    {
        # ── Persona 5: E-commerce Fraud Manager ──────────────────────────────
        "name": "Shreya Agarwal",
        "email": "shreya.agarwal@meesho.com",
        "organisation": "Meesho Inc.",
        "role": "Risk Manager",
        "org_type": "E-commerce Platform",
        "current_approach": "Third-party vendor solution",
        "txn_volume": "10 Lakh – 1 Crore",

        "pre_auth_importance": 5,
        "latency_tolerance": "Under 100ms (tolerable delay)",
        "accuracy_speed_tradeoff": "Accuracy is everything – take as long as needed",
        "explainability_importance": 3,
        "india_specific_importance": 3,

        "fr_decision_engine": 5,
        "fr_velocity": 5,
        "fr_challenge": 3,
        "fr_device": 4,
        "fr_graph": 5,
        "fr_xai": 3,
        "fr_alerts": 5,
        "fr_case_mgmt": 5,
        "fr_compliance": 3,
        "fr_merchant": 5,
        "fr_dashboard": 4,

        "nfr_uptime": "99.9% (8.7 hrs downtime/year)",
        "nfr_tps": "10,000 – 1,00,000 TPS",
        "nfr_data_residency": "No restriction",
        "nfr_log_retention": "3 years",
        "nfr_rto": "Under 2 hours",

        "fraud_types": ["mule_account", "card_fraud", "account_takeover", "money_laundering"],
        "multilang_importance": 2,

        "integration": ["rest_api", "kafka", "webhook"],
        "deployment_model": "Hybrid (on-prem + cloud)",
        "scaling_requirement": "yes",

        "pain_point": "Chargeback rates are killing our margins. We process returns-based refund fraud where buyers claim non-delivery but the item was received. We need graph analysis to detect coordinated buyer fraud rings—multiple accounts placing and disputing the same sellers.",
        "additional_requirements": "Seller/merchant risk profiling that tracks patterns across buyer-seller interaction history. Also need chargeback dispute integration with our payment gateway's dispute resolution API.",
        "comments": "Graph-based mule detection would be our flagship use case. We have strong suspicion of organised rings operating across Tier-3 cities but cannot prove it with our current tooling."
    },
    {
        # ── Persona 6: Data Scientist at a government DBT platform ────────────
        "name": "Arjun Pillai",
        "email": "arjun.pillai@nsdl.co.in",
        "organisation": "National Securities Depository Ltd. (NSDL)",
        "role": "Data Scientist / ML Engineer",
        "org_type": "Government / DBT Platform",
        "current_approach": "No automated detection currently",
        "txn_volume": "10 Lakh – 1 Crore",

        "pre_auth_importance": 3,
        "latency_tolerance": "Under 500ms (user barely notices)",
        "accuracy_speed_tradeoff": "Accuracy is everything – take as long as needed",
        "explainability_importance": 5,
        "india_specific_importance": 5,

        "fr_decision_engine": 3,
        "fr_velocity": 4,
        "fr_challenge": 2,
        "fr_device": 3,
        "fr_graph": 5,
        "fr_xai": 5,
        "fr_alerts": 3,
        "fr_case_mgmt": 4,
        "fr_compliance": 5,
        "fr_merchant": 2,
        "fr_dashboard": 4,

        "nfr_uptime": "99.9% (8.7 hrs downtime/year)",
        "nfr_tps": "100 – 1,000 TPS",
        "nfr_data_residency": "India-only (strict)",
        "nfr_log_retention": "10+ years",
        "nfr_rto": "Under 2 hours",

        "fraud_types": ["mule_account", "money_laundering", "digital_arrest"],
        "multilang_importance": 5,

        "integration": ["rest_api", "kafka"],
        "deployment_model": "On-premises (own data centre)",
        "scaling_requirement": "not required",

        "pain_point": "Beneficiary fraud in DBT is our primary concern—ghost beneficiaries, dormant accounts activated only to receive and withdraw government subsidy funds. Current detection is purely manual review by officers which is neither scalable nor consistent.",
        "additional_requirements": "Ability to ingest Aadhaar seeding data and match against beneficiary profiles for authentication. Also need quarterly model performance reports in format compatible with CAG audit requirements.",
        "comments": "The ensemble ML approach with Isolation Forest for anomaly detection is well-suited for our use case since most DBT fraud is low-frequency, high-value anomaly rather than pattern fraud. We would appreciate a pilot on our PMGSY dataset."
    }
]


# ─────────────────────────────────────────────────────────────────────────────
# Submission logic
# ─────────────────────────────────────────────────────────────────────────────

def post_json(url: str, data: dict) -> dict:
    payload = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def submit_all(base_url: str, delay: float, count: int):
    submit_url = f"{base_url.rstrip('/')}/api/survey/submit"
    print(f"\n{'='*62}")
    print(f"  ARGUS Survey Auto-Submitter  —  {count} unique respondents")
    print(f"  Target : {submit_url}")
    print(f"  Delay  : {delay}s between submissions")
    print(f"{'='*62}\n")

    used_names: set = set()
    success = 0
    failed  = 0

    for i in range(1, count + 1):
        persona = generate_persona(i, used_names)
        name = persona["name"]
        org  = persona["organisation"]
        print(f"[{i:>3}/{count}] {name:<28} | {org[:38]:<38} ... ", end="", flush=True)

        try:
            post_json(submit_url, persona)
            print("OK")
            success += 1
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8")
            print(f"FAIL  HTTP {e.code}: {body[:80]}")
            failed += 1
        except urllib.error.URLError as e:
            print(f"FAIL  Connection error: {e.reason}")
            print("\n  → Is the backend running?  uvicorn main:app --reload\n")
            failed += 1
            break
        except Exception as e:
            print(f"FAIL  {e}")
            failed += 1

        if i < count and delay > 0:
            time.sleep(delay)

    print(f"\n{'='*62}")
    print(f"  Done — {success} submitted, {failed} failed")
    print(f"  View JSON : {base_url}/api/survey/responses")
    print(f"  Export CSV: {base_url}/api/survey/export")
    print(f"  Live form : {base_url}/survey")
    print(f"{'='*62}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Auto-submit ARGUS survey — 300 unique respondents")
    parser.add_argument("--url",   default="http://localhost:8000", help="Backend base URL")
    parser.add_argument("--delay", type=float, default=0.05,        help="Seconds between submissions (default 0.05)")
    parser.add_argument("--count", type=int,   default=300,         help="Number of responses to generate (default 300)")
    args = parser.parse_args()

    submit_all(args.url, args.delay, args.count)
