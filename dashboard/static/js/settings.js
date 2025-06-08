/*----------------------------------------General Settings Section-----------------------------------------*/

function showSection(sectionId, button = null) {
    // Show the selected section
    document
        .querySelectorAll("#settingsContent section")
        .forEach((sec) => sec.classList.add("hidden"));
    document.getElementById(sectionId).classList.remove("hidden");

    // Highlight the selected button
    document
        .querySelectorAll(".sidebar-btn")
        .forEach((btn) => btn.classList.remove("bg-gray-100", "font-semibold"));
    if (button) {
        button.classList.add("bg-gray-100", "font-semibold");
    }

    // Add sectionID to url
    const url = new URL(window.location);
    url.searchParams.set("section", sectionId);

    window.history.pushState({}, "", url);
}

// Show the first section on page load
window.addEventListener("DOMContentLoaded", () => {
    const firstBtn = document.querySelector(".sidebar-btn");

    // Check if a section is specified in the URL
    const urlParams = new URLSearchParams(window.location.search);
    const section = urlParams.get("section");
    if (section) {
        const sectionElement = document.getElementById(section);
        if (sectionElement) {
            // Find the button that corresponds to the section
            const button = document.querySelector(
                `.sidebar-btn[onclick*="${section}"]`
            );
            // Show the specified section and highlight the button
            showSection(section, button);
        } else {
            // If the section doesn't exist, default to the first section
            firstBtn.click();
        }
    } else {
        // Default to the first section if no section is specified
        firstBtn.click();
    }
});

/*----------------------------------------General Settings Section End-----------------------------------------*/

/*-----------------------------------------Classifications Section-----------------------------------------*/

const rowsPerPage = 10;
let currentPage = 1;
let filteredRows = [];

function filterAndPaginate() {
    const searchValue = document
        .getElementById("hs-table-search")
        .value.toLowerCase();
    const allRows = Array.from(
        document.querySelectorAll("#classifications tbody tr")
    );

    // If search value is empty, show all rows
    if (searchValue === "") {
        filteredRows = allRows;
        currentPage = 1; // Reset to first page
        renderTable();
        return;
    }

    // Filter rows
    filteredRows = allRows.filter((row) => {
        const appName = row.children[0].textContent.toLowerCase();
        return appName.includes(searchValue);
    });

    renderTable();
}

function renderTable() {
    const tbody = document.querySelector("#classifications tbody");
    tbody.innerHTML = "";

    const start = (currentPage - 1) * rowsPerPage;
    const end = start + rowsPerPage;
    const paginatedRows = filteredRows.slice(start, end);

    paginatedRows.forEach((row) => tbody.appendChild(row));

    updatePaginationInfo();
}

function updatePaginationInfo() {
    const info = document.getElementById("paginationInfo");
    const totalPages = Math.ceil(filteredRows.length / rowsPerPage);
    info.textContent = `Page ${currentPage} of ${totalPages}`;
}

function nextPage() {
    const totalPages = Math.ceil(filteredRows.length / rowsPerPage);
    if (currentPage < totalPages) {
        currentPage++;
        renderTable();
    }
}

function prevPage() {
    if (currentPage > 1) {
        currentPage--;
        renderTable();
    }
}

// Bind search input
document.getElementById("hs-table-search").addEventListener("input", () => {
    currentPage = 1;
    filterAndPaginate();
});

// Initial setup after DOM is loaded
document.addEventListener("DOMContentLoaded", () => {
    filterAndPaginate();
});

let toggleState = {
    checkbox: null,
    appName: "",
    step: 0,
    messages: [
        "This feels suspiciously fun to *not* be a game. Care to explain?",
        "Seriously? You’re trying to sneak this past the algorithm?",
        "Alright. If your soul is clean, hit confirm. But I’m watching.",
    ],
};

function handleGameToggle(checkbox, appName) {
    if (checkbox.checked) {
        // User wants to classify this as a game (allow directly)
        updateGameClassification(appName, true);
    } else {
        // User wants to classify this AS a game — show confirmation modal
        // Temporarily re-check it so UI doesn’t flicker
        checkbox.checked = true;

        // Store intent and show modal
        toggleState.checkbox = checkbox;
        toggleState.appName = appName;
        toggleState.step = 0;
        showGameToggleModal();
    }
}

function updateGameClassification(exeName, isGame) {
    fetch(updateExeURL, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ exe_name: exeName, is_game: isGame }),
    })
        .then((response) => {
            if (!response.ok) {
                throw new Error("Network response was not ok");
            }
            return response.json();
        })
        .then((data) => {
            if (data.status === "success") {
                console.log(`${exeName} marked as: Not Game`);
            } else {
                console.error("Failed to update classification:", data.error);
            }
        })
        .catch((error) => {
            console.error("Error updating classification:", error);
        });
}

function showGameToggleModal() {
    const modal = document.getElementById("gameToggleModal");
    const message = document.getElementById("gameToggleModalMessage");
    const confirmBtn = document.getElementById("gameToggleConfirmBtn");
    const cancelBtn = document.getElementById("gameToggleCancelBtn");
    const buttonContainer = confirmBtn.parentElement;

    message.textContent = toggleState.messages[toggleState.step];
    modal.classList.remove("hidden");

    // Randomize button order
    const buttons = [confirmBtn, cancelBtn];
    let chances = Math.random();
    if (chances > 0.4) {
        buttonContainer.innerHTML = "";
        buttonContainer.appendChild(buttons[1]);
        buttonContainer.appendChild(buttons[0]);
    } else {
        buttonContainer.innerHTML = "";
        buttonContainer.appendChild(buttons[0]);
        buttonContainer.appendChild(buttons[1]);
    }
}

document
    .getElementById("gameToggleConfirmBtn")
    .addEventListener("click", () => {
        toggleState.step += 1;
        if (toggleState.step < toggleState.messages.length) {
            showGameToggleModal(); // show next confirmation
        } else {
            document.getElementById("gameToggleModal").classList.add("hidden");
            updateGameClassification(toggleState.appName, false); // final confirmation
            toggleState.checkbox.checked = false; // uncheck the checkbox
            console.log(`${toggleState.appName} marked as: Not Game`);
        }
    });

document.getElementById("gameToggleCancelBtn").addEventListener("click", () => {
    toggleState.checkbox.checked = true; // revert toggle
    document.getElementById("gameToggleModal").classList.add("hidden");
});

/*-----------------------------------------Classifications Section End-----------------------------------------*/

/*-----------------------------------------Time Limit Section-----------------------------------------*/
let confirmStepIndex = 0;
let confirmedLimit = 0;
const confirmMessages = [
    {
        title: "Level 1: Just Checking",
        message:
            "You sure you want *more* screen time? Self-control is free, you know.",
    },
    {
        title: "Level 2: Rethink Mode",
        message:
            "Okay, but like... you *do* have goals outside of gaming, right?",
    },
    {
        title: "Final Level: Grass Alert 🌱",
        message:
            "Last chance. More time means less sunlight, more regrets. Proceed?",
    },
];

function showModal(step) {
    document.getElementById("modalMessage").textContent =
        confirmMessages[step].message;
    document.getElementById("confirmModal").classList.remove("hidden");
}

function dismissModal() {
    document.getElementById("confirmModal").classList.add("hidden");
    confirmStepIndex = 0;
    confirmedLimit = 0;
}

function confirmStep() {
    confirmStepIndex++;
    if (confirmStepIndex < 3) {
        showModal(confirmStepIndex);
    } else {
        document.getElementById("confirmModal").classList.add("hidden");
        confirmStepIndex = 0;
        actuallyUpdateGlobalLimit(confirmedLimit);
    }
}

function handleGlobalLimit(input) {
    const val = parseInt(input.value);
    const message = document.getElementById("sarcasmMessage");
    const button = document.querySelector(".globalLimitButton");

    if (val > 180) {
        message.textContent =
            "🚫 Over 3 hours? Go touch some grass, hydrate, maybe even see the sun. Limit is 180 mins max.";
        button.disabled = true;
    } else {
        if (val > 120) {
            message.textContent =
                "🫠 2+ hours? Alright, just don’t forget what year it is.";
        } else if (val > 60) {
            message.textContent = "😎 1+ hour? Solid. Gamer but functioning.";
        } else if (val > 0) {
            message.textContent = "🧘 Discipline? In this economy? Impressive.";
        } else {
            message.textContent =
                "⌛ 0 mins? Either you're enlightened or lying.";
        }
        button.disabled = false;
    }
}

function updateGlobalLimit() {
    const input = document.getElementById("newLimitInput");
    const val = parseInt(input.value);
    const message = document.getElementById("sarcasmMessage");
    const currentLimit =
        parseInt(document.getElementById("currentLimitDisplay").textContent) ||
        0;

    if (isNaN(val) || val < 0) {
        message.textContent =
            "🚫 Invalid limit. Please enter a positive number.";
        return;
    }

    if (val > 180) {
        message.textContent =
            "🚫 Over 3 hours? Go touch some grass, hydrate, maybe even see the sun. Limit is 180 mins max.";
        return;
    }

    if (val > currentLimit) {
        // Ask the user 3 times before allowing increase
        confirmedLimit = val;
        confirmStepIndex = 0;
        showModal(0);
    } else {
        actuallyUpdateGlobalLimit(val);
        return;
    }

    // Set the input value back to 0
    input.value = 0;
    message.textContent = "";
}

function actuallyUpdateGlobalLimit(val) {
    const message = document.getElementById("sarcasmMessage");
    const currentLimitDisplay = document.getElementById("currentLimitDisplay");

    fetch(updateGlobalLimitURL, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ limit: val }),
    })
        .then((response) => {
            if (!response.ok) {
                throw new Error("Network response was not ok");
            }
            return response.json();
        })
        .then((data) => {
            if (data.status === "success") {
                message.textContent = `✅ Global limit set to ${val} mins. Stay strong, warrior.`;
                currentLimitDisplay.textContent = val + " mins";
            } else {
                message.textContent =
                    "❌ Failed to update limit. Error: " +
                    (data.error || "Unknown error");
            }
        })
        .catch((error) => {
            console.error("Error updating global limit:", error);
            message.textContent =
                "❌ Error updating limit. Check console for details.";
        });
}

function refreshTimeLimitList() {
    fetch(refreshTimeLimitURL, {
        method: "POST",
    })
        .then((response) => response.json())
        .then((data) => {
            if (data.status === "success") {
                // Reload the page to reflect changes
                location.reload();
            } else {
                alert("Failed to refresh time limit list: " + data.error);
            }
        })
        .catch((error) => {
            console.error("Error refreshing time limit list:", error);
            alert("An error occurred while refreshing the time limit list.");
        });
}

function handleGameLimit(button, appName) {
    const input = document.querySelector(`input[name="input-${appName}"]`);
    const val = parseInt(input.value);
    const message = document.getElementById(`infoText-${appName}`);;

    // Should be between 0-180
    if (isNaN(val) || val < 0 || val > 180) {
        message.textContent = "🚫 Invalid limit. Please enter a number between 0-180.";
        message.classList.add("text-red-500");
        return;
    }

    fetch(updateTimeLimitURL, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ exe_name: appName, max_time: val }),
    })
        .then((response) => {
            if (!response.ok) {
                throw new Error("Network response was not ok");
            }
            return response.json();
        })
        .then((data) => {
            if (data.status === "success") {
                message.textContent = `✅ Limit for ${appName} set to ${val} mins.`;
                message.classList.remove("text-red-500");
                // Set current limit display to new value
                const currentLimitDisplay = document.getElementById(`currentLimit-${appName}`);
                currentLimitDisplay.textContent = val;
            } else {
                message.textContent =
                    "❌ Failed to update limit. Error: " + data.error;
                message.classList.add("text-red-500");
            }
        })
        .catch((error) => {
            console.error("Error updating limit:", error);
            message.textContent =
                "❌ Error updating limit. Check console for details.";
            message.classList.add("text-red-500");
        });
    // Reset input value to 0 after submission
    input.value = 0;
}

/*-----------------------------------------Time Limit Section End-----------------------------------------*/

function resetAllLimits() {
    if (
        confirm("Reset all limits?") &&
        confirm("This cannot be undone.") &&
        confirm("Last chance...")
    ) {
        console.log("All limits reset.");
    }
}
