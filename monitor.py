import json
import smtplib
import os
import requests
from email.mime.text import MIMEText
from bs4 import BeautifulSoup
from datetime import datetime

# Load previously seen jobs
SEEN_JOBS_FILE = "data/last_seen.json"
if not os.path.exists(SEEN_JOBS_FILE):
    os.makedirs("data", exist_ok=True)
    with open(SEEN_JOBS_FILE, "w") as f:
        json.dump({"netflix": [], "wrapbook": []}, f)

with open(SEEN_JOBS_FILE, "r") as f:
    seen_jobs = json.load(f)

new_jobs = {"netflix": [], "wrapbook": []}

# ---------- Netflix ----------
def check_netflix_jobs():
    url = "https://explore.jobs.netflix.net/careers?query=coordinator&pid=790302362428&domain=netflix.com&sort_by=new&triggerGoButton=false&utm_source=Netflix%20Careersite"
    try:
        response = requests.get(url)
        response.raise_for_status()

        try:
            data = response.json()
        except json.JSONDecodeError:
            print("[Netflix] Failed to decode JSON. Response content:")
            print(response.text[:500])  # Preview the response
            return

        jobs = data.get("jobs", [])
        fresh = []
        for job in jobs:
            job_id = job.get("job_id")
            if job_id and job_id not in seen_jobs["netflix"]:
                seen_jobs["netflix"].append(job_id)
                fresh.append(f"Netflix: {job.get('title')} - {job.get('team')} - {job.get('location')}")

        if fresh:
            new_jobs["netflix"].extend(fresh)

    except requests.RequestException as e:
        print(f"[Netflix] Request error: {e}")


# ---------- Wrapbook ----------
def check_wrapbook_jobs():
    url = "https://www.wrapbook.com/careers#open-positions"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    listings = soup.select("a[href*='/careers/'][data-open-position]") or soup.select("a[href*='/careers/']")

    fresh = []
    for link in listings:
        title = link.get_text(strip=True)
        href = link.get("href")
        job_id = href.split("/")[-1]
        if job_id and job_id not in seen_jobs["wrapbook"]:
            seen_jobs["wrapbook"].append(job_id)
            fresh.append(f"Wrapbook: {title} - {href}")

    if fresh:
        new_jobs["wrapbook"].extend(fresh)

# ---------- Send Email ----------
def send_email_alert(new_listings):
    msg = MIMEText("\n\n".join(new_listings))
    msg["Subject"] = "🆕 New Job Listings Found"
    msg["From"] = os.environ["SMTP_SENDER"]
    msg["To"] = os.environ["SMTP_RECIPIENT"]

    with smtplib.SMTP(os.environ["SMTP_SERVER"], int(os.environ["SMTP_PORT"])) as server:
        server.starttls()
        server.login(os.environ["SMTP_USERNAME"], os.environ["SMTP_PASSWORD"])
        server.send_message(msg)

# Run all
check_netflix_jobs()
check_wrapbook_jobs()

# If new jobs, send and save
flat_list = new_jobs["netflix"] + new_jobs["wrapbook"]
if flat_list:
    send_email_alert(flat_list)

with open(SEEN_JOBS_FILE, "w") as f:
    json.dump(seen_jobs, f, indent=2)
