const carouselWrapper = document.querySelector('.swiper-wrapper');

const fetchEventsFromBackend = async () => {
    const query = `
        query {
            allEvents {
                id
                title
                event_date
                venue
                price
                image
            }
        }
    `;
    try {
        const response = await fetch('http://127.0.0.1:8000/graphql', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query })
        });
        const result = await response.json();
        // Handle Graphene's camelCase conversion if any, but we'll try to match exact key
        return result.data.allEvents;
    } catch (err) {
        console.error("Failed to fetch events, using backup data", err);
        return typeof events !== 'undefined' ? events : [];
    }
}

const createSlides = async () => {
    const liveEvents = await fetchEventsFromBackend();

    carouselWrapper.innerHTML = '';

    liveEvents.forEach((event) => {
        let slide = document.createElement('div');
        slide.className = 'swiper-slide slider';

        // Robust cleanup for display and storage
        const rawPrice = event.price || 500;
        const cleanPrice = typeof rawPrice === 'string' ? parseInt(rawPrice.replace(/[^0-9]/g, '')) || rawPrice : rawPrice;
        const displayDate = event.event_date || event.eventDate || event.date || 'TBA';

        slide.onclick = () => {
            const rawDate = displayDate;
            const lastComma = rawDate.lastIndexOf(',');
            let eventDate = rawDate;
            let eventTime = 'TBA';
            if (lastComma !== -1) {
                eventDate = rawDate.substring(0, lastComma).trim();
                eventTime = rawDate.substring(lastComma + 1).trim();
            }

            localStorage.setItem('selectedEventId', event.id);
            localStorage.setItem('selectedEvent', event.title);
            localStorage.setItem('selectedDate', eventDate);
            localStorage.setItem('selectedTime', eventTime);
            localStorage.setItem('selectedPrice', cleanPrice);
            localStorage.setItem('selectedVenue', event.venue);
            localStorage.setItem('selectedImage', event.image);
            window.location.href = 'ticket-booking.html';
        };

        slide.innerHTML = `
            <div class="slider-content">
                <p style="color: #696969; font-weight: 600; margin-bottom: 12px; font-size: 18px;">${displayDate}</p>
                <h1 style="font-size: 44px; font-weight: 800; line-height: 1.2; margin-bottom: 15px; color: #1c1c1c;">${event.title}</h1>
                <p style="font-size: 20px; color: #696969; margin-bottom: 8px;">${event.venue}</p>
                <p style="font-size: 24px; font-weight: 700; color: #1c1c1c;">₹${cleanPrice}</p>
            </div>
            <img src="${event.image}" class="slider-image" alt="${event.title}">
        `;
        carouselWrapper.appendChild(slide);
    });

    // Re-init swiper after slides are added
    if (typeof Swiper !== 'undefined') {
        new Swiper('.swiper', {
            loop: true,
            autoplay: { delay: 3000, disableOnInteraction: false },
            pagination: { el: '.swiper-pagination', clickable: true },
            navigation: { nextEl: '.swiper-button-next', prevEl: '.swiper-button-prev' },
        });
    }
}

createSlides();

// Side navigation bar
jQuery(document).ready(function ($) {
    $('.open-menu').on('click', function (e) {
        e.preventDefault();
        $('.sidebar').toggleClass('active');
        $('.overlay').toggleClass('active');
    });

    $('.login, .overlay').on('click', function () {
        $('.sidebar').removeClass('active');
        $('.overlay').removeClass('active');
    });
});

// Get the modal
var modal = document.getElementById('id01');

// When the user clicks anywhere outside of the modal, close it
window.onclick = function (event) {
    if (event.target == modal) {
        modal.style.display = "none";
    }
}
