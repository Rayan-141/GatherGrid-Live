from graphene import ObjectType, String, Int, Float, List, Field
from db import get_driver


# ── Seat ──────────────────────────────────────────────────────────
class SeatObject(ObjectType):
    id = Int()
    seat_number = String()
    category = String()
    price = Float()
    status = String()


# ── Ticket ────────────────────────────────────────────────────────
class TicketObject(ObjectType):
    id = Int()
    qr_code = String()
    seat = Field(SeatObject)

    def resolve_seat(self, info):
        with get_driver().session() as session:
            result = session.run("""
                MATCH (t:Ticket {id: $ticket_id})-[:FOR_SEAT]->(s:Seat)
                RETURN s
            """, ticket_id=self.id)
            record = result.single()
            if record:
                s = record["s"]
                return SeatObject(
                    id=s.get("id"),
                    seat_number=s.get("seat_number"),
                    price=s.get("price", 0),
                    status=s.get("status", "available")
                )
        return None


# ── Payment ───────────────────────────────────────────────────────
class PaymentObject(ObjectType):
    id = Int()
    amount = Float()
    payment_status = String()
    payment_date = String()


# ── Event ─────────────────────────────────────────────────────────
class SeatFilterInput(ObjectType):
    status = String()


class EventObject(ObjectType):
    id = Int()
    title = String()
    description = String()
    venue = String()
    event_date = String()
    total_seats = Int()
    price = Float()
    seats = List(SeatObject, filter=String())

    def resolve_seats(self, info, filter=None):
        event_id = int(self.id or 0)
        print(f"🔍 DEBUG: Resolving seats for Event ID: {event_id} (Type: {type(event_id)})", flush=True)
        with get_driver().session() as session:
            if filter:
                # Filter seats by status
                result = session.run("""
                    MATCH (e:Event)-[:HAS_SEAT]->(s:Seat)
                    WHERE e.id = $event_id AND s.status = $status
                    RETURN s
                """, event_id=event_id, status=filter)
            else:
                result = session.run("""
                    MATCH (e:Event)-[:HAS_SEAT]->(s:Seat)
                    WHERE e.id = $event_id
                    RETURN s
                """, event_id=event_id)

            seats = []
            for record in result:
                s = record["s"]
                seats.append(SeatObject(id=s["id"], seat_number=s["seat_number"],
                                        price=s.get("price", 0), status=s["status"]))
            
            print(f"✅ DEBUG: Found {len(seats)} seats for Event {event_id}", flush=True)
            return seats


# ── Booking ───────────────────────────────────────────────────────
class BookingObject(ObjectType):
    id = Int()
    booking_date = String()
    total_amount = Float()
    status = String()
    event_name = String()
    seats_booked = String()
    event = Field(EventObject)
    tickets = List(TicketObject)
    payment = Field(PaymentObject)

    def resolve_event(self, info):
        with get_driver().session() as session:
            result = session.run("""
                MATCH (b:Booking {id: $booking_id})-[:FOR_EVENT]->(e:Event)
                RETURN e
            """, booking_id=self.id)
            record = result.single()
            if record:
                e = record["e"]
                return EventObject(
                    id=e.get("id"),
                    title=e.get("title"),
                    description=e.get("description", "No description available"),
                    venue=e.get("venue", "TBA"),
                    event_date=e.get("event_date", "TBA"),
                    total_seats=e.get("total_seats", 0)
                )
        return None

    def resolve_tickets(self, info):
        with get_driver().session() as session:
            result = session.run("""
                MATCH (b:Booking {id: $booking_id})-[:HAS_TICKET]->(t:Ticket)
                RETURN t
            """, booking_id=self.id)
            tickets = []
            for record in result:
                t = record["t"]
                tickets.append(TicketObject(id=t["id"], qr_code=t["qr_code"]))
            return tickets

    def resolve_payment(self, info):
        with get_driver().session() as session:
            result = session.run("""
                MATCH (b:Booking {id: $booking_id})-[:HAS_PAYMENT]->(p:Payment)
                RETURN p
            """, booking_id=self.id)
            record = result.single()
            if record:
                p = record["p"]
                return PaymentObject(id=p["id"], amount=p["amount"],
                                     payment_status=p["payment_status"], payment_date=p["payment_date"])
        return None


# ── User ──────────────────────────────────────────────────────────
class UserObject(ObjectType):
    id = String()
    name = String()
    email = String()
    phone = String()
    bookings = List(BookingObject)

    def resolve_bookings(self, info):
        with get_driver().session() as session:
            result = session.run("""
                MATCH (u:User {email: $email})-[:MADE_BOOKING]->(b:Booking)
                RETURN b
            """, email=self.email)
            bookings = []
            for record in result:
                b = record["b"]
                bookings.append(BookingObject(id=b["id"], booking_date=b["booking_date"],
                                              total_amount=b["total_amount"], status=b["status"]))
            return bookings
