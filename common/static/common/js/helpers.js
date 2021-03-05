function swapImage(input) {
    // Helper function which reads a file and re-renders a src tag of a tag matching the #imagePreview id
    if (input.files && input.files[0]) {
        let reader = new FileReader();

        reader.onload = function (e) {
            document.getElementById('imagePreview').src = e.target.result;
        };

        reader.readAsDataURL(input.files[0]);
    }
}