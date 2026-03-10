const API_URL = 'http://127.0.0.1:8000/graphql';

/**
 * Generic function to talk to the GraphQL backend
 */
async function fetchGraphQL(query, variables = {}) {
    try {
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ query, variables }),
        });
        const result = await response.json();
        if (result.errors) {
            console.error('GraphQL Errors:', result.errors);
            throw new Error(result.errors[0].message);
        }
        return result.data;
    } catch (error) {
        console.error('Fetch Error:', error);
        throw error;
    }
}

/**
 * Creates a booking using real user data from the frontend
 */
async function apiCreateBooking(userData, eventId, seatIds, eventMetadata) {
    const mutation = `
        mutation CreateBooking($input: CreateBookingInput!) {
            create_booking(input: $input) {
                booking {
                    id
                    status
                    total_amount
                    event_name
                    seats_booked
                }
            }
        }
    `;

    const variables = {
        input: {
            user_name: userData.name,
            user_email: userData.email,
            user_phone: userData.phone,
            event_id: parseInt(eventId),
            event_title: eventMetadata.title,
            event_venue: eventMetadata.venue,
            event_date: eventMetadata.date,
            event_price: parseFloat(eventMetadata.price),
            event_image: eventMetadata.image,
            seat_numbers: seatIds
        }
    };

    const data = await fetchGraphQL(mutation, variables);
    return data.create_booking.booking;
}

/**
 * Confirms payment in the Neo4j database
 */
async function apiConfirmPayment(bookingId, amount) {
    const mutation = `
        mutation confirm_payment($bookingId: Int!, $amount: Float!) {
            confirm_payment(booking_id: $bookingId, amount: $amount) {
                payment {
                    id
                    payment_status
                }
            }
        }
    `;

    const variables = {
        bookingId: parseInt(bookingId),
        amount: parseFloat(amount)
    };

    const data = await fetchGraphQL(mutation, variables);
    return data.confirm_payment.payment;
}
