from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Ticket
from .forms import TicketForm

@login_required
def ticket_list(request):
    tickets = Ticket.objects.filter(user=request.user)
    return render(request, 'support/ticket_list.html', {'tickets': tickets})

@login_required
def create_ticket(request):
    if request.method == 'POST':
        form = TicketForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.user = request.user
            ticket.save()
            messages.success(request, 'Support ticket created successfully. We will get back to you soon.')
            return redirect('support:list')
    else:
        # Pre-fill name and email
        form = TicketForm(initial={'name': request.user.first_name or 'User', 'email': request.user.email})
    
    return render(request, 'support/ticket_form.html', {'form': form})

@login_required
def ticket_detail(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id, user=request.user)
    return render(request, 'support/ticket_detail.html', {'ticket': ticket})
