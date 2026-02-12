// Modal interactions

// Display modal with input text content
function textModal(content) {
  const modal = document.getElementById('modal');
  modal.style.display = 'block';

  container = modal.getElementsByClassName('modal-content')[0];
  container.textContent = content;
}

// Display modal with static content
function staticModal() {
  const modal = document.getElementById('modal');
  modal.style.display = 'block';
}

// Close modal
function closeModal() {
  const modal = document.getElementById('modal');
  modal.style.display = 'none';
}

// Close modal if clicked outside of modal
window.onclick = function(event) {
  if (event.target == modal) {
    modal.style.display = 'none';
  }
}
