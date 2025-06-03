document.addEventListener("DOMContentLoaded", function () {
  // Sidebar Toggle
  const sidebar = document.querySelector(".sidebar");
  const sidebarToggles = document.querySelectorAll(".sidebar-toggle");

  sidebarToggles.forEach((toggle) => {
    toggle.addEventListener("click", () => {
      sidebar.classList.toggle("collapsed");

      // Save sidebar state
      localStorage.setItem(
        "sidebarCollapsed",
        sidebar.classList.contains("collapsed")
      );
    });
  });

  // Restore sidebar state
  if (localStorage.getItem("sidebarCollapsed") === "true") {
    sidebar.classList.add("collapsed");
  }

  // Mobile sidebar
  if (window.innerWidth < 992) {
    sidebar.classList.add("collapsed");
  }

  // Close sidebar when clicking outside on mobile
  document.addEventListener("click", (event) => {
    if (window.innerWidth < 992) {
      if (
        !sidebar.contains(event.target) &&
        !event.target.closest(".sidebar-toggle")
      ) {
        sidebar.classList.remove("show");
      }
    }
  });

  // Initialize tooltips
  const tooltipTriggerList = [].slice.call(
    document.querySelectorAll('[data-bs-toggle="tooltip"]')
  );
  tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl);
  });

  // Initialize popovers
  const popoverTriggerList = [].slice.call(
    document.querySelectorAll('[data-bs-toggle="popover"]')
  );
  popoverTriggerList.map(function (popoverTriggerEl) {
    return new bootstrap.Popover(popoverTriggerEl);
  });

  // File Upload Preview
  const fileInputs = document.querySelectorAll('input[type="file"]');
  fileInputs.forEach((input) => {
    input.addEventListener("change", function () {
      const preview = document.querySelector(this.dataset.preview);
      if (preview && this.files && this.files[0]) {
        const reader = new FileReader();

        reader.onload = function (e) {
          if (preview.tagName === "IMG") {
            preview.src = e.target.result;
          } else {
            preview.style.backgroundImage = `url(${e.target.result})`;
          }
        };

        reader.readAsDataURL(this.files[0]);
      }
    });
  });

  // Delete Confirmation
  const deleteButtons = document.querySelectorAll("[data-delete-url]");
  deleteButtons.forEach((button) => {
    button.addEventListener("click", function (e) {
      e.preventDefault();

      const url = this.dataset.deleteUrl;
      const name = this.dataset.deleteName || "Bu öğe";

      if (
        confirm(
          `${name} silinecek. Bu işlem geri alınamaz. Devam etmek istiyor musunuz?`
        )
      ) {
        const form = document.createElement("form");
        form.method = "POST";
        form.action = url;

        // Add CSRF token
        const csrfToken = document.querySelector(
          'meta[name="csrf-token"]'
        ).content;
        const csrfInput = document.createElement("input");
        csrfInput.type = "hidden";
        csrfInput.name = "csrf_token";
        csrfInput.value = csrfToken;
        form.appendChild(csrfInput);

        document.body.appendChild(form);
        form.submit();
      }
    });
  });

  // Table Search
  const tableSearch = document.querySelector(".table-search");
  if (tableSearch) {
    const input = tableSearch.querySelector("input");
    const table = document.querySelector(tableSearch.dataset.target);

    if (input && table) {
      input.addEventListener("keyup", function () {
        const searchText = this.value.toLowerCase();
        const rows = table.querySelectorAll("tbody tr");

        rows.forEach((row) => {
          const text = row.textContent.toLowerCase();
          row.style.display = text.includes(searchText) ? "" : "none";
        });
      });
    }
  }

  // Sortable Tables
  const sortableTables = document.querySelectorAll(".table-sortable");
  sortableTables.forEach((table) => {
    const headers = table.querySelectorAll("th[data-sort]");

    headers.forEach((header) => {
      header.addEventListener("click", function () {
        const sortBy = this.dataset.sort;
        const sortOrder = this.dataset.order === "asc" ? "desc" : "asc";

        // Update sort order
        headers.forEach((h) => (h.dataset.order = ""));
        this.dataset.order = sortOrder;

        // Sort table
        const tbody = table.querySelector("tbody");
        const rows = Array.from(tbody.querySelectorAll("tr"));

        rows.sort((a, b) => {
          const aValue = a.querySelector(`td[data-${sortBy}]`).dataset[sortBy];
          const bValue = b.querySelector(`td[data-${sortBy}]`).dataset[sortBy];

          if (sortOrder === "asc") {
            return aValue > bValue ? 1 : -1;
          } else {
            return aValue < bValue ? 1 : -1;
          }
        });

        rows.forEach((row) => tbody.appendChild(row));
      });
    });
  });

  // Charts
  const chartElements = document.querySelectorAll("[data-chart]");
  chartElements.forEach((element) => {
    const ctx = element.getContext("2d");
    const type = element.dataset.chart;
    const data = JSON.parse(element.dataset.chartData);
    const options = JSON.parse(element.dataset.chartOptions || "{}");

    new Chart(ctx, {
      type: type,
      data: data,
      options: {
        responsive: true,
        maintainAspectRatio: false,
        ...options,
      },
    });
  });

  // Toast Notifications
  window.showToast = function (message, type = "success") {
    const toast = document.createElement("div");
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.setAttribute("role", "alert");
    toast.setAttribute("aria-live", "assertive");
    toast.setAttribute("aria-atomic", "true");

    toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;

    document.body.appendChild(toast);
    const bsToast = new bootstrap.Toast(toast, {
      animation: true,
      autohide: true,
      delay: 3000,
    });
    bsToast.show();

    toast.addEventListener("hidden.bs.toast", () => {
      document.body.removeChild(toast);
    });
  };

  // Form Validation
  const forms = document.querySelectorAll(".needs-validation");
  forms.forEach((form) => {
    form.addEventListener("submit", function (event) {
      if (!form.checkValidity()) {
        event.preventDefault();
        event.stopPropagation();
      }

      form.classList.add("was-validated");
    });
  });

  // Image Gallery
  const galleryItems = document.querySelectorAll(".gallery-item");
  galleryItems.forEach((item) => {
    item.addEventListener("click", function () {
      const img = this.querySelector("img");
      const modal = new bootstrap.Modal(document.getElementById("imageModal"));
      const modalImg = document.querySelector("#imageModal img");

      if (modalImg) {
        modalImg.src = img.src;
        modal.show();
      }
    });
  });

  // Print Functionality
  const printButtons = document.querySelectorAll(".btn-print");
  printButtons.forEach((button) => {
    button.addEventListener("click", function () {
      window.print();
    });
  });
});
