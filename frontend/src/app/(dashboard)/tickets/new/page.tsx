import { CreateTicketForm } from "@/components/tickets/CreateTicketForm";

export default function NewTicketPage() {
  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-900">Nueva solicitud</h1>
        <p className="text-sm text-gray-500 mt-1">Completa el formulario para abrir un nuevo ticket de soporte.</p>
      </div>
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <CreateTicketForm />
      </div>
    </div>
  );
}
