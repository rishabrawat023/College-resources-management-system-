// ============================================================
// script.js - small helpers for the pages
// ============================================================

// 1. Ask "Are you sure?" before deleting / cancelling / removing.
//    Any <form data-confirm="message"> gets this behaviour.
document.querySelectorAll("form[data-confirm]").forEach(function (form) {
    form.addEventListener("submit", function (event) {
        if (!confirm(form.dataset.confirm)) {
            event.preventDefault();   // stop the form from being sent
        }
    });
});


// 2. Booking page only
var bookingForm = document.getElementById("booking-form");

if (bookingForm) {
    var resourceSelect = document.getElementById("resource_id");
    var capacityHint = document.getElementById("capacity-hint");
    var startInput = document.getElementById("start_time");
    var endInput = document.getElementById("end_time");
    var checkButton = document.getElementById("check-button");
    var resultText = document.getElementById("availability-result");

    // Show the capacity of the chosen resource under the dropdown
    function showCapacity() {
        var option = resourceSelect.options[resourceSelect.selectedIndex];
        if (option && option.dataset.capacity) {
            capacityHint.textContent = "Capacity: " + option.dataset.capacity + " students";
        } else {
            capacityHint.textContent = "";
        }
    }
    resourceSelect.addEventListener("change", showCapacity);
    showCapacity();

    // End time must be later than start time ("HH:MM" text compares correctly)
    function endIsAfterStart() {
        return endInput.value > startInput.value;
    }

    bookingForm.addEventListener("submit", function (event) {
        if (!endIsAfterStart()) {
            alert("End time must be after the start time.");
            event.preventDefault();
        }
    });

    // "Check availability" button: asks the server (app.py) and shows the answer
    checkButton.addEventListener("click", function () {
        // Only the resource, date and times are needed to check availability
        if (!resourceSelect.value || !document.getElementById("date").value ||
            !startInput.value || !endInput.value) {
            resultText.textContent = "Choose a resource, date, start time and end time first.";
            resultText.className = "availability-result bad";
            return;
        }
        if (!endIsAfterStart()) {
            resultText.textContent = "End time must be after the start time.";
            resultText.className = "availability-result bad";
            return;
        }

        var query = new URLSearchParams(new FormData(bookingForm)).toString();

        fetch(bookingForm.dataset.checkUrl + "?" + query)
            .then(function (response) { return response.json(); })
            .then(function (data) {
                resultText.textContent = data.message;
                resultText.className = "availability-result " + (data.available ? "ok" : "bad");
            })
            .catch(function () {
                resultText.textContent = "Could not check availability. Is the server running?";
                resultText.className = "availability-result bad";
            });
    });
}
