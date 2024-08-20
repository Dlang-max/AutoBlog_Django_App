import os
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from .models import Member
from .config import plan_to_blogs_per_month, plan_to_price_id, price_id_to_plan, membership_level_indices
from .decorators import member_required
import stripe
import stripe.webhook

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")
stripe.api_key = STRIPE_SECRET_KEY

@login_required(login_url='login/')
@user_passes_test(member_required, login_url='member_info')
def pay(request):
    user = request.user
    try:
        member = Member.objects.get(user=user)
    except Member.DoesNotExist:
        return redirect('member_info')
    
    return render(request, 'autoblog/pay.html', {"member" : member})

@login_required(login_url='login/')
def create_checkout_session(request):
    if request.method == "POST":
        user = request.user
        member = Member.objects.get(user=user)
        customer = stripe.Customer.create()

        if member.membership_level != "none":
            stripe.Subscription.cancel(member.stripe_subscription_id)


        option = request.POST['payment']
        if option in plan_to_price_id:
            membership_level = plan_to_price_id[option]
            domain = "http://localhost:1337"

            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[
                    {
                        'price' : membership_level,
                        'quantity' : 1,
                    },
                ],
                customer=customer,
                mode='subscription',
                success_url=domain + "/dashboard/",
                cancel_url=domain + "/dashboard/",
            )

            member.stripe_customer_id = customer.id
            member.save()
            return redirect(checkout_session.url)
        
    
    return redirect('pay')

# UPDATE SUBSCRIPTION
# MEMBER INFO UPDATE HANDLED IN WEBHOOK
@login_required(login_url='login/')
def handle_subscription_update(request):
    if request.method == 'POST':
        option = request.POST['payment']
        if option in plan_to_price_id:
            try:
                member = Member.objects.get(user=request.user)
                stripe_customer_id = member.stripe_customer_id
                stripe_subscription_id = member.stripe_subscription_id
                member_subscription_info = stripe.Subscription.list(customer=stripe_customer_id)
                
                stripe.Subscription.modify(
                    stripe_subscription_id,
                    items=[{"id": member_subscription_info['data'][0]['items']['data'][0]['id'], "price": plan_to_price_id[option]}],
                )
            except stripe.InvalidRequestError:
                pass

    return redirect("dashboard")

# CANCEL SUBSCRIPTION
# MEMBER INFO UPDATE HANDLED IN WEBHOOK
@login_required(login_url='login/')
def handle_subscription_cancelled(request):
    if request.method == 'POST':
        member = Member.objects.get(user=request.user)
        try:
            stripe.Subscription.cancel(member.stripe_subscription_id)
        except stripe.InvalidRequestError:
            pass

    return redirect("dashboard")

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        return HttpResponse("Value Error", status=400)
    except stripe.error.SignatureVerificationError as e:
        return HttpResponse("Signature Verification Error", status=400)
    
    match event['type']:
        # HANDLE STRIPE CHECKOUT
        case 'checkout.session.completed':
            handle_member_checkout(event=event)

        # HANDLE UPDATES TO MEMBER SUBSCRIPTIONS
        case 'customer.subscription.updated':
            handle_member_update(event=event)

        # HANDLE MONTHLY PAYMENTS
        case 'invoice.payment_succeeded':
            handle_monthly_payment(event=event)

        # HANDLE SUBSCRIPTION CANCELLATIONS
        case 'customer.subscription.deleted':
            handle_member_cancellation(event=event)
 
    return HttpResponse(status=200)

# HELPER METHODS
# Implement Error Handling
#############################################################################
def handle_member_checkout(event):
    """ Handles updating member information after successful first time stripe 
    checkout

    Args:
        event: The stripe webhook event sent after a member checks out with stripe 
    """
    session = event['data']['object'] 
    customer_id = session["customer"]
    subscription_id = session['subscription']
    member = Member.objects.get(stripe_customer_id=customer_id)
    member.has_paid = True
    member.stripe_subscription_id = subscription_id
    member.save()


def handle_member_update(event):
    """ Handles updating member information after a member joins a subscription plan

    Args:
        event: The stripe webhook event sent after a member updates their account
    """
    session = event['data']['object']
    customer_id = session["customer"]
    membership_level = session['items']['data'][0]['plan']['id']
    new_membership_level = price_id_to_plan[membership_level]
    member = Member.objects.get(stripe_customer_id=customer_id)
    member.membership_level = new_membership_level

    membership_level_index = membership_level_indices[new_membership_level]
    member.membership_level_index = membership_level_index

    if membership_level_index >= 3:
        member.on_automated_plan = True
    else:
        member.on_automated_plan = False


    member.save()


def handle_monthly_payment(event):
    """ Handles updating member information after a member successfully pays their 
    monthly invoice

    Args:
        event: The stripe webhook event sent after a member successfully pays their
        monthly invoice
    """
    session = event['data']['object']
    customer_id = session["customer"]
    member = Member.objects.get(stripe_customer_id=customer_id)
    member.blogs_remaining += plan_to_blogs_per_month[member.membership_level]
    member.save()


def handle_member_cancellation(event):
    """ Handles updating member information after a member cancels their subscription

    Args:
        event: The stripe webhook event sent after a member successfully cancels
        their account
    """
    session = event['data']['object']
    customer_id = session['customer']

    member = Member.objects.get(stripe_customer_id=customer_id)

    member.has_paid = False
    member.stripe_customer_id = ''
    member.stripe_subscription_id = ''
    member.membership_level = 'none'
    member.membership_level_index = -1

    member.on_automated_plan = False
    member.automated_mode_on = False
    
    member.save()