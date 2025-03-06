document.addEventListener("DOMContentLoaded", function () {
    function calculateRowHours(row) {
        let morningIn = row.querySelector('input[name="morning_in"]').value;
        let morningOut = row.querySelector('input[name="morning_out"]').value;
        let afternoonIn = row.querySelector('input[name="afternoon_in"]').value;
        let afternoonOut = row.querySelector('input[name="afternoon_out"]').value;
        let totalCell = row.querySelector('.total-hours');

        function timeDiff(start, end) {
            if (!start || !end) return 0;
            let startTime = new Date(`2000-01-01T${start}:00`);
            let endTime = new Date(`2000-01-01T${end}:00`);
            return (endTime - startTime) / (1000 * 60 * 60); // Convert milliseconds to hours
        }

        let totalHours = timeDiff(morningIn, morningOut) + timeDiff(afternoonIn, afternoonOut);
        totalCell.textContent = totalHours.toFixed(2);

        updateTotalWeekHours();
    }

    function updateTotalWeekHours() {
        let total = 0;
        document.querySelectorAll('.total-hours').forEach(cell => {
            total += parseFloat(cell.textContent) || 0;
        });

        let totalWeekHoursElement = document.getElementById('total-week-hours');
        if (totalWeekHoursElement) {
            totalWeekHoursElement.textContent = total.toFixed(2);
        }

        console.log("Total Week Hours Updated:", total.toFixed(2));
    }

    function setDayBasedOnDate(input) {
        let dateValue = input.value;
        if (!dateValue) return;

        let date = new Date(dateValue);
        let days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

        let row = input.closest('tr');
        let dayCell = row.querySelector('.day-text');
        if (dayCell) {
            dayCell.textContent = days[date.getDay()];
        }
    }

    function addEventListeners() {
        document.querySelectorAll('tr.timesheet-row').forEach(row => {
            row.querySelectorAll('input[type="time"]').forEach(input => {
                input.addEventListener('change', () => calculateRowHours(row));
            });

            let dateInput = row.querySelector('input[type="date"]');
            if (dateInput) {
                dateInput.addEventListener('change', () => setDayBasedOnDate(dateInput));
            }
        });
    }

    function deleteEntry(date) {
        if (confirm("Are you sure you want to delete this entry?")) {
            fetch(`/delete_entry/${date}`, { method: "POST" })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        let row = document.getElementById(`row-${date}`);
                        if (row) {
                            row.remove();
                            updateTotalWeekHours(); // Update weekly total after deletion
                        }
                    } else {
                        alert("Failed to delete entry.");
                    }
                })
                .catch(error => console.error("Error:", error));
        }
    }

    addEventListeners();
});
