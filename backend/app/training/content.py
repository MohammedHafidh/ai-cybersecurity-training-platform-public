"""Versioned, curated lessons and deterministic knowledge checks. No generated grading."""

from copy import deepcopy

VERSION = "training-2.0"
SCENARIOS = {
    "brute-force": {
        "title": "Brute Force",
        "source": "auth",
        "scenario": "brute_force",
        "eyebrow": "01 / Authentication",
        "objective": "Read failed-login evidence and distinguish a burst from ordinary retries.",
        "definition": "Brute force is repeated credential guessing. A failed login is evidence of a failed attempt, not proof that an account was compromised.",
        "importance": "Authentication logs help defenders investigate password guessing while recognizing legitimate mistakes.",
        "activity": "The approved client makes three bounded failed SSH login attempts against the isolated authentication target.",
        "observe": "Look for three failed-password records. Match their timestamps and source before counting them.",
        "logs": "OpenSSH records a timestamp, attempted username, source and outcome. The browser redacts identifying values while preserving failure evidence.",
        "features": {
            "failed_login_count": "Count the displayed failure records assigned to this source and 60-second window.",
            "attempt_count": "Count all accepted password events in the same window.",
            "attempts_per_second": "Attempts divided by the fixed 60-second window, not by the gap between events.",
            "unique_username_count": "Number of different attempted usernames before redaction.",
            "successful_login_count": "Successful password events in this window.",
            "success_after_failure": "Whether a later success follows an earlier failure.",
        },
        "rule": "The frozen rule alerts at three failed password events in a source/target group within a fixed 60-second UTC window.",
        "ml": "The frozen Logistic Regression model reads counts, rates and related authentication features. It does not read the trusted label or use Ollama.",
        "limitations": "A person retrying a password can trigger the rule. Slow guessing or activity split across window boundaries may be missed. A prediction is not proof of compromise.",
        "mitigation": "Use MFA, sensible rate limits, strong credentials and investigation of repeated failures. Balance lockout policies against denial-of-service risks.",
        "references": [
            {
                "title": "MITRE ATT&CK T1110: Brute Force",
                "url": "https://attack.mitre.org/techniques/T1110/",
            }
        ],
        "quiz": [
            (
                "Which record directly supports a failed password attempt?",
                [
                    "A failed SSH password event",
                    "A model probability",
                    "A quiz score",
                    "A page visit",
                ],
                0,
                "The original authentication event records the outcome; predictions are derived later.",
            ),
            (
                "Three attempts in a fixed 60-second window give what attempt rate?",
                [
                    "3 per second",
                    "60 per second",
                    "0.05 per second",
                    "The rate cannot be calculated",
                ],
                2,
                "The feature uses 3 / 60 = 0.05 attempts per second.",
            ),
            (
                "Where does the expected label come from?",
                [
                    "Ollama",
                    "Controlled-run metadata",
                    "The rule threshold",
                    "Agreement between detectors",
                ],
                1,
                "The collection protocol establishes ground truth independently of either detector.",
            ),
            (
                "Why might an alert be a false positive?",
                [
                    "Every failed login is an attack",
                    "ML never makes mistakes",
                    "A citation changes the label",
                    "A legitimate user may retry a password",
                ],
                3,
                "Ordinary retries can resemble guessing, so inspect context rather than assume compromise.",
            ),
        ],
    },
    "sql-injection": {
        "title": "SQL Injection",
        "source": "web",
        "scenario": "sql_injection",
        "eyebrow": "02 / Web security",
        "objective": "Connect request evidence to token features without treating a keyword as proof of exploitation.",
        "definition": "SQL injection occurs when untrusted input changes the structure or meaning of a database query.",
        "importance": "Unsafe query construction can expose data or permit unintended operations. Request indicators need contextual interpretation.",
        "activity": "The approved client sends one predefined bounded request to a deliberately vulnerable isolated target containing disposable fake data.",
        "observe": "Read the sanitized request and decoded input, then locate the SQL-like indicator counted by the feature.",
        "logs": "The target records request time, method, path, decoded input, response status and the controlled run marker. Responses alone do not prove exploitation.",
        "features": {
            "suspicious_token_count": "Matches of the frozen SQL-like indicator expression in decoded request input.",
            "max_request_length": "Length of the longest decoded input, not the full HTTP request.",
            "request_count": "Number of accepted requests in this run.",
            "error_response_count": "Requests with HTTP status 400 or above.",
            "empty_input_count": "Present inputs containing no characters.",
            "missing_input_count": "Requests with no input field.",
            "residual_encoded_count": "Inputs still containing percent-encoded patterns after the configured decoding step.",
        },
        "rule": "The frozen rule alerts when at least one SQL-like token match occurs across the web run.",
        "ml": "The frozen model combines request length, token, missingness and response features. The model produces a benign/malicious classification, not an exploitation verdict.",
        "limitations": "Harmless SQL-like prose can cause false positives. Other injection syntax may evade the token rule. The frozen benchmark includes misses; no examples are relabeled to improve scores.",
        "mitigation": "Use parameterized queries and least-privilege database access. Validate input for the intended type; escaping and keyword blocking are not substitutes for parameterization.",
        "references": [
            {
                "title": "OWASP SQL Injection",
                "url": "https://community.owasp.org/attacks/SQL_Injection",
            },
            {
                "title": "OWASP SQL Injection Prevention",
                "url": "https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html",
            },
        ],
        "quiz": [
            (
                "What primarily prevents input from changing SQL query structure?",
                [
                    "A longer password",
                    "Parameterized queries",
                    "An orange warning",
                    "A model score",
                ],
                1,
                "Parameterized queries keep values separate from query structure.",
            ),
            (
                "A SQL-like word in input proves what?",
                [
                    "A database was stolen",
                    "The request succeeded",
                    "The user is malicious",
                    "An indicator needs investigation",
                ],
                3,
                "The rule matches indicators; benign prose can also match.",
            ),
            (
                "What does maximum request length mean here?",
                [
                    "Longest decoded input length",
                    "All network bytes",
                    "Number of rows returned",
                    "Seconds since startup",
                ],
                0,
                "The implemented feature measures decoded input length.",
            ),
            (
                "If ground truth is malicious but the rule predicts benign, this is a…",
                ["True negative", "False positive", "False negative", "Correct detection"],
                2,
                "A false negative misses a malicious controlled run; ground truth must remain unchanged.",
            ),
        ],
    },
    "reconnaissance": {
        "title": "Reconnaissance",
        "source": "network",
        "scenario": "reconnaissance",
        "eyebrow": "03 / Network evidence",
        "objective": "Explain port diversity, connection counts and fixed-window rates from observed service connections.",
        "definition": "Network reconnaissance discovers available services. Connections to different ports can be consistent with discovery, but may also be authorized administration.",
        "importance": "Defenders need to understand both service discovery patterns and the limits of their telemetry.",
        "activity": "The approved client performs one bounded connect scan of the two predefined internal target ports. No external address or custom port is accepted.",
        "observe": "Compare the scan report with timestamped target connection records. Count connections and distinct destination ports separately.",
        "logs": "Target-side records supply connection timestamps and accepted ports. The scan report corroborates port observations; it cannot supply individual connection timing by itself.",
        "features": {
            "connection_count": "Number of recorded accepted connections within the same source/target window.",
            "unique_destination_port_count": "Number of different destination ports, regardless of repeated connections to one port.",
            "connections_per_second": "Connection count divided by the fixed 60-second window.",
            "observed_span_seconds": "Time between the earliest and latest recorded connections; this is not the rate denominator.",
        },
        "rule": "The frozen rule alerts at two distinct observed destination ports in a fixed 60-second source/target window.",
        "ml": "The frozen model reads connection count, fixed-window rate, observed span and port diversity. Some malicious held-out network runs were missed.",
        "limitations": "Authorized multi-service connections can trigger the rule. Only instrumented accepted connections are observed; closed-port probing may not appear. The frozen ML network recall was zero on two malicious held-out runs.",
        "mitigation": "Limit unnecessary exposed services, use appropriate network filtering and monitor service discovery with contextual review. Authorized scans must be distinguishable from unknown activity.",
        "references": [
            {
                "title": "MITRE ATT&CK T1046: Network Service Discovery",
                "url": "https://attack.mitre.org/techniques/T1046/",
            }
        ],
        "quiz": [
            (
                "Three connections to one port produce how many distinct ports?",
                ["Three", "Sixty", "One", "Zero"],
                2,
                "Port diversity counts distinct destination port values, not total connections.",
            ),
            (
                "Which evidence supplies individual accepted-connection timestamps?",
                [
                    "Target-side connection logs",
                    "A quiz answer",
                    "The model label",
                    "A list of open ports alone",
                ],
                0,
                "The instrumented service logs provide the connection timestamps.",
            ),
            (
                "What denominator does the connection-rate feature use?",
                ["Observed span", "60 seconds", "Number of ports", "Model probability"],
                1,
                "This pipeline uses a fixed 60-second window, even when events occur close together.",
            ),
            (
                "Can normal administration resemble reconnaissance?",
                [
                    "No, never",
                    "Only if Ollama says so",
                    "Only after changing ground truth",
                    "Yes, so inspect context and limitations",
                ],
                3,
                "Authorized multi-service access can create the same simple indicators.",
            ),
        ],
    },
}

SAFETY = "Only the approved isolated local Docker lab is used. No external targets, custom commands, ports or payloads are accepted. Real exercises require the operator's preconfigured private lab bundle."


def lesson(key, *, answers=False):
    value = deepcopy(SCENARIOS[key])
    quiz = value.pop("quiz")
    value.update(
        id=key,
        version=VERSION,
        safety=SAFETY,
        objectives=[
            value["objective"],
            "Trace evidence into features and independent predictions.",
            "Recognize uncertainty and explain a defensive lesson.",
        ],
        steps=[
            "Read the objective and safety boundary.",
            "Start the approved controlled exercise.",
            "Observe logs, events and features.",
            "Compare ground truth with rule and ML outputs.",
            "Ask a grounded question and complete the knowledge check.",
        ],
        questions=[
            dict(
                id=f"q{i+1}",
                prompt=q[0],
                options=q[1],
                **({"correct": q[2], "explanation": q[3]} if answers else {}),
            )
            for i, q in enumerate(quiz)
        ],
    )
    return value
