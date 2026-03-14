import requests
import os

def send_push_report():
    topic = "flarkaudio_reports"
    report_path = "P:/git/DJwerk/REPORTS.md"
    
    if not os.path.exists(report_path):
        return

    with open(report_path, "r", encoding="utf-8") as f:
        report_content = f.read()

    try:
        # Push de inhoud van het rapport naar ntfy.sh
        requests.post(f"https://ntfy.sh/{topic}", 
                      data=report_content.encode('utf-8'),
                      headers={
                          "Title": "?? DJwerk Status Report",
                          "Priority": "high",
                          "Tags": "cd,musical_note"
                      })
        print(f">> PUSH REPORT SENT TO ntfy.sh/{topic}")
    except Exception as e:
        print(f"[ERROR] Failed to push report: {e}")

if __name__ == "__main__":
    send_push_report()
