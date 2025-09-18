from flask import Flask, jsonify, render_template
import os, uuid, time
import redis
import psycopg2

app = Flask(__name__)

# ---------- helpers ----------

def get_db_conn():
    return psycopg2.connect(
        host="database",
        dbname=os.getenv("POSTGRES_DB", "appdb"),
        user=os.getenv("POSTGRES_USER", "appuser"),
        password=os.getenv("POSTGRES_PASSWORD", "apppass")
    )

def check_services():
    result = {
        "redis": {"ok": False},
        "postgres": {"ok": False},
        "errors": {}
    }

    # ---------- REDIS PROOF ----------
    try:
        r = redis.Redis(host="cache", port=6379, db=0)
        pong = r.ping()  # real ping

        # increment a counter + set last-check timestamp
        cnt = r.incr("lab:status:counter")
        r.set("lab:status:last_check", int(time.time()))

        # quick facts
        dbsize = r.dbsize()
        mem = r.info("memory").get("used_memory_human", "n/a")

        result["redis"].update({
            "ok": bool(pong),
            "ping": "pong" if pong else "fail",
            "counter": cnt,
            "dbsize": dbsize,
            "used_memory": mem
        })
    except Exception as e:
        result["errors"]["redis"] = str(e)

    # ---------- POSTGRES PROOF ----------
    try:
        conn = get_db_conn()
        conn.autocommit = True
        with conn.cursor() as cur:
            # ensure table exists
            cur.execute("""
                CREATE TABLE IF NOT EXISTS proof (
                    id UUID PRIMARY KEY,
                    note TEXT NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
            """)

            # insert one row each check with a unique id
            uid = str(uuid.uuid4())
            cur.execute("INSERT INTO proof (id, note) VALUES (%s, %s);",
                        (uid, "compose-connected"))

            # count rows
            cur.execute("SELECT COUNT(*) FROM proof;")
            rowcount = cur.fetchone()[0]

            # server version
            cur.execute("SHOW server_version;")
            ver = cur.fetchone()[0]
        conn.close()

        result["postgres"].update({
            "ok": True,
            "rows_in_proof": rowcount,
            "server_version": ver,
            "last_insert_id": uid
        })
    except Exception as e:
        result["errors"]["postgres"] = str(e)

    return result

# ---------- routes ----------

@app.get("/")
def home():
    info = check_services()
    return render_template("index.html", info=info)

@app.get("/status")
def status():
    return jsonify(check_services())

@app.post("/reset")
def reset():
    """Clears demo data so counters/rows don't grow forever."""
    res = {"redis": None, "postgres": None}

    # reset Redis keys
    try:
        r = redis.Redis(host="cache", port=6379, db=0)
        # delete returns the number of keys removed
        deleted = r.delete("lab:status:counter", "lab:status:last_check")
        res["redis"] = {"deleted_keys": int(deleted)}
    except Exception as e:
        res["redis"] = {"error": str(e)}

    # truncate Postgres table
    try:
        conn = get_db_conn()
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS proof (
                    id UUID PRIMARY KEY,
                    note TEXT NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
            """)
            cur.execute("TRUNCATE TABLE proof;")
        conn.close()
        res["postgres"] = {"truncated": True}
    except Exception as e:
        res["postgres"] = {"error": str(e)}

    return jsonify({"ok": True, "result": res})

# optional tiny health endpoint (handy for healthchecks)
@app.get("/healthz")
def healthz():
    try:
        r = redis.Redis(host="cache", port=6379, db=0)
        if not r.ping():
            return jsonify({"ok": False}), 503
        conn = get_db_conn()
        conn.close()
        return jsonify({"ok": True})
    except Exception:
        return jsonify({"ok": False}), 503


if __name__ == "__main__":
    # Flask dev server (fine for this lab)
    app.run(host="0.0.0.0", port=8080)
