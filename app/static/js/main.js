// Image Preview for File Uploads
function previewImage(input, previewElement) {
  if (input.files && input.files[0]) {
    const reader = new FileReader();

    reader.onload = function (e) {
      const preview = document.querySelector(previewElement);
      preview.src = e.target.result;
      preview.style.display = "block";
    };

    reader.readAsDataURL(input.files[0]);
  }
}

// Quantity Input Validation
function validateQuantity(input) {
  const value = parseInt(input.value);
  const max = parseInt(input.getAttribute("max"));
  const min = parseInt(input.getAttribute("min"));

  if (value > max) input.value = max;
  if (value < min) input.value = min;
}

// Price Range Slider
function updatePriceRange(minInput, maxInput, minValue, maxValue) {
  const min = parseInt(minInput.value);
  const max = parseInt(maxInput.value);

  if (min > max) {
    if (minInput === document.activeElement) {
      minInput.value = max;
    } else {
      maxInput.value = min;
    }
  }

  minValue.textContent = `$${minInput.value}`;
  maxValue.textContent = `$${maxInput.value}`;
}

// Search Form Submission
function handleSearch(event) {
  const searchInput = document.querySelector("#search-input");
  if (!searchInput.value.trim()) {
    event.preventDefault();
    searchInput.focus();
  }
}

// Flash Message Auto-dismiss
document.addEventListener("DOMContentLoaded", function () {
  const alerts = document.querySelectorAll(".alert");
  alerts.forEach(function (alert) {
    setTimeout(function () {
      const closeButton = alert.querySelector(".btn-close");
      if (closeButton) {
        closeButton.click();
      }
    }, 5000);
  });
});

// Mobile Menu Toggle
function toggleMobileMenu() {
  const navbarCollapse = document.querySelector(".navbar-collapse");
  navbarCollapse.classList.toggle("show");
}

// Form Validation
function validateForm(form) {
  const requiredFields = form.querySelectorAll("[required]");
  let isValid = true;

  requiredFields.forEach(function (field) {
    if (!field.value.trim()) {
      isValid = false;
      field.classList.add("is-invalid");
    } else {
      field.classList.remove("is-invalid");
    }
  });

  return isValid;
}

// Add to Cart Animation
function addToCartAnimation(button) {
  button.classList.add("adding-to-cart");
  setTimeout(() => {
    button.classList.remove("adding-to-cart");
  }, 1000);
}

// Category Filter
function filterProducts(categoryId) {
  const url = new URL(window.location.href);
  if (categoryId) {
    url.searchParams.set("category", categoryId);
  } else {
    url.searchParams.delete("category");
  }
  window.location.href = url.toString();
}

// Price Filter
function filterByPrice(min, max) {
  const url = new URL(window.location.href);
  if (min) url.searchParams.set("min_price", min);
  if (max) url.searchParams.set("max_price", max);
  window.location.href = url.toString();
}

// Sort Products
function sortProducts(sortBy) {
  const url = new URL(window.location.href);
  url.searchParams.set("sort", sortBy);
  window.location.href = url.toString();
}

// Initialize Tooltips
document.addEventListener("DOMContentLoaded", function () {
  const tooltipTriggerList = [].slice.call(
    document.querySelectorAll('[data-bs-toggle="tooltip"]')
  );
  tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl);
  });
});

// Image Lazy Loading
document.addEventListener("DOMContentLoaded", function () {
  const lazyImages = document.querySelectorAll("img[data-src]");

  if ("IntersectionObserver" in window) {
    const imageObserver = new IntersectionObserver((entries, observer) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const img = entry.target;
          img.src = img.dataset.src;
          img.removeAttribute("data-src");
          imageObserver.unobserve(img);
        }
      });
    });

    lazyImages.forEach((img) => imageObserver.observe(img));
  } else {
    // Fallback for browsers that don't support IntersectionObserver
    lazyImages.forEach((img) => {
      img.src = img.dataset.src;
      img.removeAttribute("data-src");
    });
  }
});

// Add to Cart Functionality
function addToCart(productId, quantity = 1) {
  fetch("/cart/add", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": document.querySelector('meta[name="csrf-token"]').content,
    },
    body: JSON.stringify({
      product_id: productId,
      quantity: quantity,
    }),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        // Sepet sayısını güncelle
        const cartCountElement = document.querySelector(".cart-count");
        if (cartCountElement) {
          cartCountElement.textContent = data.cart_count;
        }

        // Başarı mesajı göster
        showToast(data.message, "success");

        // Animasyon ekle
        const button = document.querySelector(
          `[onclick="addToCart(${productId})"]`
        );
        if (button) {
          addToCartAnimation(button);
        }
      } else {
        showToast(data.message, "error");
      }
    })
    .catch((error) => {
      console.error("Error:", error);
      showToast("Bir hata oluştu", "error");
    });
}

// Toast mesajı gösterme fonksiyonu
function showToast(message, type = "success") {
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
}

// Initialize all necessary event listeners
document.addEventListener("DOMContentLoaded", function () {
  // Search form
  const searchForm = document.querySelector("#search-form");
  if (searchForm) {
    searchForm.addEventListener("submit", handleSearch);
  }

  // Quantity inputs
  const quantityInputs = document.querySelectorAll(".quantity-input");
  quantityInputs.forEach((input) => {
    input.addEventListener("change", () => validateQuantity(input));
  });

  // File upload previews
  const fileInputs = document.querySelectorAll('input[type="file"]');
  fileInputs.forEach((input) => {
    input.addEventListener("change", () => {
      const previewElement = input.dataset.preview;
      if (previewElement) {
        previewImage(input, previewElement);
      }
    });
  });

  // Add to cart buttons
  const addToCartButtons = document.querySelectorAll(".add-to-cart");
  addToCartButtons.forEach((button) => {
    button.addEventListener("click", (e) => {
      e.preventDefault();
      const productId = button.dataset.productId;
      const quantityInput = document.querySelector(`#quantity-${productId}`);
      const quantity = quantityInput ? parseInt(quantityInput.value) : 1;
      addToCart(productId, quantity);
    });
  });
});
