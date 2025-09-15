  // Basic Javascript for Modal Popup
        const checkoutBtn = document.getElementById('checkoutBtn');
        const checkoutModal = document.getElementById('checkoutModal');
        const closeModalBtn = document.getElementById('closeModalBtn');
        const modalContent = document.getElementById('modalContent');

        function openModal() {
            checkoutModal.classList.remove('hidden');
            checkoutModal.classList.add('flex');
            modalContent.classList.remove('modal-leave');
            modalContent.classList.add('modal-enter');
        }

        function closeModal() {
            modalContent.classList.remove('modal-enter');
            modalContent.classList.add('modal-leave');
            setTimeout(() => {
                checkoutModal.classList.add('hidden');
                checkoutModal.classList.remove('flex');
            }, 300); // Wait for animation to finish
        }

        checkoutBtn.addEventListener('click', openModal);
        closeModalBtn.addEventListener('click', closeModal);
        checkoutModal.addEventListener('click', (e) => {
            if (e.target === checkoutModal) {
                closeModal();
            }
        });