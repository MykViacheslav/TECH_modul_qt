#!/usr/bin/env python3
import argparse
import subprocess
import re
from datetime import date
from pathlib import Path


def parse_pytest_summary(text: str) -> dict:
    summary = {"total": 0, "passed": 0, "failed": 0, "skipped": 0}
    # Look for lines like: 'X passed', 'Y failed', 'Z skipped'
    for m in re.finditer(r"(\d+)\s+(passed|failed|skipped)", text):
        count = int(m.group(1))
        kind = m.group(2)
        summary[kind] = summary.get(kind, 0) + count
        summary["total"] = summary["total"] + count
    return summary


def md_to_html(md: str) -> str:
    lines = md.splitlines()
    html = []
    in_code = False
    for line in lines:
        if line.strip().startswith("``"):
            in_code = not in_code
            html.append('<pre><code>' if in_code else '</code></pre>')
            continue
        if in_code:
            html.append(line.replace('<','&lt;').replace('>','&gt;'))
            continue
        if line.startswith('# '):
            html.append('<h1>' + line[2:] + '</h1>')
        elif line.startswith('## '):
            html.append('<h2>' + line[3:] + '</h2>')
        elif line.strip():
            html.append('<p>' + line + '</p>')
        else:
            html.append('<br/>')
    return '<html><body>' + ''.join(html) + '</body></html>'


def run_and_generate(html: bool, csv: bool):
    # Run tests (full output)
    result = subprocess.run(["pytest"], capture_output=True, text=True)
    stdout = result.stdout
    stderr = result.stderr
    summary = parse_pytest_summary(stdout + stderr)

    today = date.today().strftime("%Y%m%d")
    reports_dir = Path("reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    md_path = reports_dir / f"test_report_{today}.md"
    md_content = []
    md_content.append("# Automated Test Report\n")
    md_content.append(f"Date: {date.today().isoformat()}\n\n")
    md_content.append("## Summary\n")
    md_content.append(f"Total tests: {summary['total']}\n")
    md_content.append(f"Passed: {summary['passed']}\n")
    md_content.append(f"Failed: {summary['failed']}\n")
    md_content.append(f"Skipped: {summary['skipped']}\n\n")
    md_content.append("## Details\n\n")
    md_content.append("```\n" + stdout + "\n```")
    md_text = "".join(md_content)
    md_path.write_text(md_text, encoding="utf-8")

    if html:
        html_path = reports_dir / f"test_report_{today}.html"
        html_content = md_to_html(md_text)
        html_path.write_text(html_content, encoding="utf-8")
        print(f"HTML report written to {html_path}")
    if csv:
        csv_path = reports_dir / f"test_report_{today}.csv"
        with csv_path.open("w", encoding="utf-8") as f:
            f.write("date,total,passed,failed,skipped\n")
            f.write(f"{today},{summary['total']},{summary['passed']},{summary['failed']},{summary['skipped']}\n")
        print(f"CSV report written to {csv_path}")

    print(f"MD report written to {md_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--html", action="store_true", help="generate HTML report")
    parser.add_argument("--csv", action="store_true", help="generate CSV report")
    args = parser.parse_args()
    run_and_generate(html=args.html, csv=args.csv)


if __name__ == '__main__':
    main()
