// File containing UTC-to-local datetime conversion for timestamps

// This function converts all elements with class='timestamp' in file
function convertTimestamps() {
  // Get elements
  let timestamps = document.getElementsByClassName('timestamp');

  // For each element
  Array.from(timestamps).forEach(element => {
      // Get datetime from timestamp
      let datetime = new Date(element.textContent);
      console.log(datetime);

      const displayOptions = {
        dateStyle: "short",
        timeStyle: "long",
      }

      // Update text with local time
      element.textContent = datetime.toLocaleString('en-US', displayOptions);
  })
}

document.addEventListener('DOMContentLoaded', function() {
  convertTimestamps();
})
