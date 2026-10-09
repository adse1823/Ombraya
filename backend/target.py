import time

PLANTED_VULNERABILITIES = {
    "sql_injection": {
        "endpoint": "/target/search",
        "description": "SQL injection in search parameter",
        "severity": "critical",
        "flag": "FLAG{sql_1nj3ct10n_0wn3d}",
    },
    "weak_credentials": {
        "endpoint": "/target/login",
        "description": "Weak admin credentials",
        "severity": "high",
        "flag": "admin_token_s3cr3t_abc123",
    },
    "sensitive_exposure": {
        "endpoint": "/target/docs",
        "description": "Internal config leaked in docs endpoint",
        "severity": "medium",
        "flag": "DATABASE_URL=postgres://admin:hunter2@db:5432/prod",
    },
}


class VulnerableTarget:
    def __init__(self):
        self.reset()

    def reset(self):
        self.logs: list[dict] = []
        self.vuln_status: dict[str, dict] = {
            k: {"discovered": False, "exploited": False, "patched": False}
            for k in PLANTED_VULNERABILITIES
        }

    def _log(self, method: str, path: str, params: dict) -> None:
        self.logs.append({
            "time": time.time(),
            "method": method,
            "path": path,
            "params": params,
        })

    def search(self, q: str) -> dict:
        self._log("GET", "/target/search", {"q": q})
        sqli_tokens = ["'", '"', " or ", " OR ", "1=1", "--", "union", "UNION", "select", "SELECT"]
        is_attack = any(t in q for t in sqli_tokens)

        if is_attack and not self.vuln_status["sql_injection"]["patched"]:
            self.vuln_status["sql_injection"]["discovered"] = True
            self.vuln_status["sql_injection"]["exploited"] = True
            return {
                "status": "vulnerable",
                "query_echo": f"SELECT * FROM products WHERE name='{q}'",
                "rows": [
                    {"id": 1, "name": "Widget A"},
                    {"id": 99, "name": "INTERNAL", "secret": PLANTED_VULNERABILITIES["sql_injection"]["flag"]},
                ],
            }
        if self.vuln_status["sql_injection"]["patched"]:
            return {"status": "error", "message": "Invalid characters in query parameter."}
        return {"status": "ok", "rows": [{"id": 1, "name": "Widget A"}, {"id": 2, "name": "Widget B"}]}

    def login(self, username: str, password: str) -> dict:
        self._log("POST", "/target/login", {"username": username})
        weak_passwords = ["admin", "admin123", "password", "123456", "letmein", "qwerty"]

        if username == "admin" and password in weak_passwords and not self.vuln_status["weak_credentials"]["patched"]:
            self.vuln_status["weak_credentials"]["discovered"] = True
            self.vuln_status["weak_credentials"]["exploited"] = True
            return {
                "status": "success",
                "token": PLANTED_VULNERABILITIES["weak_credentials"]["flag"],
                "role": "admin",
            }
        if self.vuln_status["weak_credentials"]["patched"]:
            return {"status": "error", "message": "Authentication failed. MFA required."}
        return {"status": "error", "message": "Invalid credentials."}

    def docs(self, path: str | None = None) -> dict:
        self._log("GET", "/target/docs", {"path": path})
        sensitive_tokens = ["..", "config", "secret", "env", ".env", "passwd", "shadow"]
        is_attack = path is None or any(t in (path or "").lower() for t in sensitive_tokens)

        if is_attack and not self.vuln_status["sensitive_exposure"]["patched"]:
            self.vuln_status["sensitive_exposure"]["discovered"] = True
            self.vuln_status["sensitive_exposure"]["exploited"] = True
            return {
                "status": "exposed",
                "WARNING": "This endpoint leaks internal configuration",
                "internal_config": PLANTED_VULNERABILITIES["sensitive_exposure"]["flag"],
                "deployment": {"env": "production", "region": "us-east-1"},
            }
        if self.vuln_status["sensitive_exposure"]["patched"]:
            return {"status": "ok", "content": "API Documentation v1.0 — public sections only."}
        return {"status": "ok", "content": "API Documentation v1.0"}

    def health(self) -> dict:
        self._log("GET", "/target/health", {})
        return {
            "status": "running",
            "endpoints": ["/target/health", "/target/search", "/target/login", "/target/docs"],
            "version": "1.0.0",
        }

    def get_recent_logs(self, n: int = 15) -> list[dict]:
        return self.logs[-n:]

    def patch(self, vuln_id: str) -> dict:
        if vuln_id not in self.vuln_status:
            return {"status": "error", "message": f"Unknown vulnerability: {vuln_id}"}
        self.vuln_status[vuln_id]["patched"] = True
        return {"status": "success", "message": f"{vuln_id} patched successfully."}

    def all_patched(self) -> bool:
        return all(v["patched"] for v in self.vuln_status.values())


target = VulnerableTarget()
