/**
 * CineBook Interactive Seat Map — Modern Indian Cinema Edition
 * Handles live seat fetching, keyboard navigation, max-seat limits, and ₹ INR pricing calculation.
 */
document.addEventListener("DOMContentLoaded", () => {
  const container = document.getElementById("seat-map-container");
  if (!container) return;

  const showId = container.dataset.showId;
  const unitPrice = parseFloat(container.dataset.price) || 0;
  const seatLimitWarning = document.getElementById("seat-limit-warning");
  const badgesContainer = document.getElementById("selected-seats-badges");
  const totalPriceElem = document.getElementById("summary-total-price");
  const seatIdsInput = document.getElementById("seat_ids_input");
  const confirmBtn = document.getElementById("confirm-booking-btn");
  const bookingForm = document.getElementById("booking-form");

  const MAX_SEATS = 6;
  const selectedSeats = new Map(); // seatId -> { label, id }

  // Load seats from the JSON API
  fetch(`/api/shows/${showId}/seats`)
    .then(response => {
      if (!response.ok) {
        throw new Error("Failed to load auditorium seating layout.");
      }
      return response.json();
    })
    .then(data => {
      renderSeatGrid(data);
    })
    .catch(err => {
      container.innerHTML = `
        <div class="empty-state">
          <p class="form-error">Could not load seats: ${err.message}</p>
          <button class="btn btn-secondary btn-sm" onclick="location.reload()">Retry</button>
        </div>
      `;
    });

  function renderSeatGrid(data) {
    container.innerHTML = "";

    // Group seats by row label
    const rowsMap = new Map();
    data.seats.forEach(seat => {
      if (!rowsMap.has(seat.row)) {
        rowsMap.set(seat.row, []);
      }
      rowsMap.get(seat.row).push(seat);
    });

    const gridWrapper = document.createElement("div");
    gridWrapper.className = "seat-grid-table";
    gridWrapper.setAttribute("role", "grid");
    gridWrapper.setAttribute("aria-label", "Auditorium Seat Map");

    rowsMap.forEach((seatsInRow, rowLabel) => {
      const rowDiv = document.createElement("div");
      rowDiv.className = "seat-row";
      rowDiv.setAttribute("role", "row");

      // Left row label
      const leftLabel = document.createElement("span");
      leftLabel.className = "row-marker";
      leftLabel.textContent = rowLabel;
      rowDiv.appendChild(leftLabel);

      // Seats container
      const seatsRow = document.createElement("div");
      seatsRow.className = "seats-row-items";

      seatsInRow.forEach(seat => {
        const seatBtn = document.createElement("button");
        seatBtn.type = "button";
        seatBtn.className = `seat ${seat.is_booked ? "seat-booked" : "seat-available"}`;
        seatBtn.dataset.seatId = seat.id;
        seatBtn.dataset.label = seat.label;
        seatBtn.setAttribute("role", "gridcell");
        seatBtn.setAttribute("aria-label", `Row ${seat.row} Seat ${seat.number}, ${seat.is_booked ? "Sold Out" : "Available"}`);
        seatBtn.textContent = seat.is_booked ? "✕" : seat.number;

        if (seat.is_booked) {
          seatBtn.disabled = true;
          seatBtn.setAttribute("aria-disabled", "true");
        } else {
          seatBtn.setAttribute("aria-pressed", "false");
          seatBtn.tabIndex = 0;

          seatBtn.addEventListener("click", () => toggleSeat(seatBtn, seat));
          seatBtn.addEventListener("keydown", (e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              toggleSeat(seatBtn, seat);
            }
          });
        }

        seatsRow.appendChild(seatBtn);
      });

      rowDiv.appendChild(seatsRow);

      // Right row label
      const rightLabel = document.createElement("span");
      rightLabel.className = "row-marker";
      rightLabel.textContent = rowLabel;
      rowDiv.appendChild(rightLabel);

      gridWrapper.appendChild(rowDiv);
    });

    container.appendChild(gridWrapper);
  }

  function toggleSeat(button, seat) {
    const seatId = seat.id;

    if (selectedSeats.has(seatId)) {
      // Deselect
      selectedSeats.delete(seatId);
      button.classList.remove("seat-selected");
      button.classList.add("seat-available");
      button.setAttribute("aria-pressed", "false");
      seatLimitWarning.style.display = "none";
    } else {
      // Select
      if (selectedSeats.size >= MAX_SEATS) {
        seatLimitWarning.style.display = "block";
        return;
      }
      seatLimitWarning.style.display = "none";
      selectedSeats.set(seatId, { id: seatId, label: seat.label });
      button.classList.remove("seat-available");
      button.classList.add("seat-selected");
      button.setAttribute("aria-pressed", "true");
    }

    updateSummary();
  }

  function updateSummary() {
    const count = selectedSeats.size;

    // Badges update
    badgesContainer.innerHTML = "";
    if (count === 0) {
      badgesContainer.innerHTML = '<span class="empty-badge">Click any available seat on the map</span>';
      confirmBtn.disabled = true;
      seatIdsInput.value = "";
      totalPriceElem.textContent = "₹0";
      confirmBtn.innerHTML = '<span class="btn-lock-icon">🔒</span><span class="btn-text">Proceed to Pay</span>';
    } else {
      selectedSeats.forEach(seat => {
        const badge = document.createElement("span");
        badge.className = "badge badge-accent seat-tag";
        badge.textContent = seat.label;
        badgesContainer.appendChild(badge);
      });
      confirmBtn.disabled = false;
      seatIdsInput.value = Array.from(selectedSeats.keys()).join(",");

      // Price calculation in ₹ INR
      const total = Math.round(count * unitPrice);
      totalPriceElem.textContent = `₹${total}`;
      confirmBtn.innerHTML = `<span class="btn-lock-icon">🔒</span><span class="btn-text">Pay ₹${total} (Simulated)</span>`;
    }
  }

  if (bookingForm) {
    bookingForm.addEventListener("submit", () => {
      confirmBtn.disabled = true;
      confirmBtn.innerHTML = "<span>Processing Reservation...</span>";
    });
  }
});
