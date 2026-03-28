import { TicketDetail } from "@/components/tickets/TicketDetail";

export default function TicketDetailPage({ params }: { params: { id: string } }) {
  return <TicketDetail ticketId={params.id} />;
}
