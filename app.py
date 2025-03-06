import csv
import os
from flask import Flask, render_template, request, session, send_file, redirect, jsonify
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "your_secret_key"

CSV_FILE = "timesheet.csv"

def initialize_csv():
    """Creates an empty timesheet CSV file with headers."""
    with open(CSV_FILE, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([
            "full_name", "college_year", "company_name", "company_address",
            "date", "day", "morning_in", "morning_out", "afternoon_in", "afternoon_out", "total_hours"
        ])

def save_to_csv(timesheet):
    """Saves timesheet data to CSV."""
    with open(CSV_FILE, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([
            "full_name", "college_year", "company_name", "company_address",
            "date", "day", "morning_in", "morning_out", "afternoon_in", "afternoon_out", "total_hours"
        ])
        for entry in timesheet:
            writer.writerow([
                session.get("full_name", ""),
                session.get("college_year", ""),
                session.get("company_name", ""),
                session.get("company_address", ""),
                entry["date"],
                entry["day"],
                entry["morning_in"],
                entry["morning_out"],
                entry["afternoon_in"],
                entry["afternoon_out"],
                entry["total_hours"]
            ])

def load_from_csv():
    """Loads timesheet data from CSV."""
    if not os.path.exists(CSV_FILE):
        initialize_csv()
        return []
    
    timesheet = []
    with open(CSV_FILE, mode="r") as file:
        reader = csv.DictReader(file)
        for row in reader:
            row["total_hours"] = float(row["total_hours"])
            row["deletable"] = False  # Prevents deletion of loaded data
            timesheet.append(row)
    return timesheet

def calculate_hours(start, end):
    """Calculates the total hours between two time entries."""
    if not start or not end:
        return 0
    fmt = "%H:%M" 
    try:
        start_time = datetime.strptime(start, fmt)
        end_time = datetime.strptime(end, fmt)
        return (end_time - start_time).total_seconds() / 3600
    except ValueError:
        return 0

def get_day_from_date(date_str):
    """Returns the day of the week for a given date."""
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        return date_obj.strftime("%A")
    except ValueError:
        return "Invalid Date"

def adjust_to_weekday(predicted_date):
    """Ensure the predicted date falls on a weekday (Monday–Friday)."""
    while predicted_date.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
        predicted_date += timedelta(days=1)  # Move to next Monday
    return predicted_date

def predict_completion_date(timesheet, required_hours):
    """Predicts the completion date based on average daily hours worked."""
    if not timesheet or required_hours == 0:
        return None  # Return None instead of a string

    total_week_hours = sum(float(entry["total_hours"]) for entry in timesheet)
    remaining_hours = max(0, required_hours - total_week_hours)

    if remaining_hours == 0:
        return None  # Return None when already completed

    days_with_hours = [float(entry["total_hours"]) for entry in timesheet if float(entry["total_hours"]) > 0]
    avg_daily_hours = sum(days_with_hours) / len(days_with_hours) if days_with_hours else 0

    if avg_daily_hours == 0:
        return None

    estimated_days_needed = remaining_hours / avg_daily_hours
    last_date_str = max(entry["date"] for entry in timesheet)
    last_date = datetime.strptime(last_date_str, "%Y-%m-%d")
    completion_date = last_date + timedelta(days=int(round(estimated_days_needed)))

    # Adjust the completion date to a weekday
    adjusted_date = adjust_to_weekday(completion_date)

    return adjusted_date  # Return datetime object instead of string


@app.route("/", methods=["GET", "POST"])
def index():
    """Handles the main page and timesheet entries."""
    if "timesheet" not in session:
        session["timesheet"] = load_from_csv()
    timesheet = session["timesheet"]
    
    if request.method == "POST":
        if "save_details" in request.form:
            session["full_name"] = request.form.get("full_name", "")  
            session["college_year"] = request.form.get("college_year", "")
            session["company_name"] = request.form.get("company_name", "")
            session["company_address"] = request.form.get("company_address", "")
            session.modified = True  # Mark session as modified

        if "program" in request.form:
            session["required_hours"] = int(request.form["program"])
            session.modified = True

        if "add_entry" in request.form:
            date = request.form.get("date")
            morning_in = request.form.get("morning_in")
            morning_out = request.form.get("morning_out")
            afternoon_in = request.form.get("afternoon_in")
            afternoon_out = request.form.get("afternoon_out")

            if date:
                total_hours = calculate_hours(morning_in, morning_out) + calculate_hours(afternoon_in, afternoon_out)
                new_entry = {
                    "date": date,
                    "day": get_day_from_date(date),
                    "morning_in": morning_in,
                    "morning_out": morning_out,
                    "afternoon_in": afternoon_in,
                    "afternoon_out": afternoon_out,
                    "total_hours": f"{total_hours:.2f}",
                    "deletable": True,
                }
                timesheet.append(new_entry)
                session["timesheet"] = timesheet
                session.modified = True
                save_to_csv(timesheet)

    total_week_hours = sum(float(entry["total_hours"]) for entry in timesheet)
    required_hours = session.get("required_hours", 0)
    remaining_hours = max(0, required_hours - total_week_hours) if required_hours else "N/A"
    predicted_completion_date = predict_completion_date(timesheet, required_hours)

    return render_template("index.html", timesheet=timesheet, total_week_hours=f"{total_week_hours:.2f}", required_hours=required_hours, remaining_hours=remaining_hours, predicted_completion_date=predicted_completion_date, full_name=session.get("full_name", ""), college_year=session.get("college_year", ""), company_name=session.get("company_name", ""), company_address=session.get("company_address", ""))


@app.route("/download/csv")
def download_csv():
    """Downloads the timesheet as a CSV file."""
    return send_file(CSV_FILE, as_attachment=True)

@app.route("/download/pdf")
def download_pdf():
    """Downloads the timesheet as a PDF file."""
    pdf_file = "timesheet_report.pdf"
    generate_pdf(session.get("timesheet", []), pdf_file)
    return send_file(pdf_file, as_attachment=True)

@app.route("/reset", methods=["POST"])
def reset():
    """Resets the session and timesheet.csv file."""
    session.clear()
    session.modified = True

    # Delete and reinitialize the CSV file
    if os.path.exists(CSV_FILE):
        os.remove(CSV_FILE)
    
    initialize_csv()  # Ensure the CSV file remains structured

    return redirect("/")


@app.route("/delete_entry/<date>", methods=["DELETE"])
def delete_entry(date):
    """Deletes a specific timesheet entry by date."""
    if "timesheet" in session:
        session["timesheet"] = [entry for entry in session["timesheet"] if entry["date"] != date]
        session.modified = True  # Ensure session updates
        save_to_csv(session["timesheet"])  # Save updated list to CSV
    return jsonify({"success": True})

def generate_pdf(timesheet, filename):
    """Generates a PDF report of the timesheet."""
    c = canvas.Canvas(filename, pagesize=letter)
    c.setFont("Helvetica", 12)
    
    # Header Information
    y_position = 750
    c.drawString(100, y_position, f"Full Name: {session.get('full_name', 'N/A')}")
    c.drawString(100, y_position - 20, f"College Year: {session.get('college_year', 'N/A')}")
    c.drawString(100, y_position - 40, f"Company Name: {session.get('company_name', 'N/A')}")
    c.drawString(100, y_position - 60, f"Company Address: {session.get('company_address', 'N/A')}")
    c.drawString(100, y_position - 80, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # **Retrieve Predicted Completion Date**
    predicted_completion_date = session.get("predicted_completion_date")
    predicted_completion_date_str = (
        predicted_completion_date.strftime("%Y-%m-%d") if predicted_completion_date else "N/A"
    )
    c.drawString(100, y_position - 100, f"Predicted Completion Date: {predicted_completion_date_str}")

    # **Retrieve Total and Remaining Hours**
    total_hours = sum(float(entry["total_hours"]) for entry in timesheet)
    required_hours = session.get("required_hours", 0)
    remaining_hours = max(0, required_hours - total_hours) if required_hours else "N/A"

    c.drawString(100, y_position - 120, f"Total Hours: {total_hours:.2f}")
    c.drawString(100, y_position - 140, f"Remaining Hours: {remaining_hours}")

    # **Move Table Below New Fields**
    y_position -= 180  # Adjust position

    # Table Headers
    headers = ["Date", "Day", "Morning In", "Morning Out", "Afternoon In", "Afternoon Out", "Total Hours"]
    col_widths = [80, 80, 80, 80, 80, 80, 80]  # Adjust column widths as needed

    c.setFont("Helvetica-Bold", 10)
    x_position = 50
    for i, header in enumerate(headers):
        c.drawString(x_position, y_position, header)
        x_position += col_widths[i]
    
    # Table Rows
    c.setFont("Helvetica", 10)
    y_position -= 20  # Move to the next row
    
    for entry in timesheet:
        x_position = 50
        row_data = [
            entry["date"], entry["day"], entry["morning_in"], entry["morning_out"],
            entry["afternoon_in"], entry["afternoon_out"], entry["total_hours"]
        ]
        for i, data in enumerate(row_data):
            c.drawString(x_position, y_position, str(data))
            x_position += col_widths[i]
        y_position -= 20  # Move to the next row

        # Prevent going off-page (handle pagination)
        if y_position < 50:
            c.showPage()
            c.setFont("Helvetica", 10)
            y_position = 750  # Reset y-position for new page

    c.save()


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)

