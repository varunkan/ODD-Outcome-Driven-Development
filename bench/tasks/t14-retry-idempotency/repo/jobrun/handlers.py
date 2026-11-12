"""The job kinds the tills submit. A handler takes the job and a context and returns a JSON-able output.

Payloads (amounts in whole cents):

- charge_invoice: {"invoice", "account", "amount"}                  charge the account
- split_charge:   {"invoice", "parts": [{"account", "amount"}, ...]}  charge each part, in order
- refund:         {"invoice", "account", "amount"}                  refund the account
- send_receipt:   {"invoice", "account", "amount", "email"}         charge the account, then mail a receipt
- notify:         {"email", "subject", "body"}                      mail a message
"""


def _amount(value):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError('an amount is a positive whole number of cents, not %r' % (value,))
    return value


def _field(payload, name):
    try:
        value = payload[name]
    except KeyError:
        raise ValueError('payload has no %r' % name) from None
    if not isinstance(value, str) or not value:
        raise ValueError('payload %r must be a non-empty string' % name)
    return value


def charge_invoice(job, ctx):
    p = job.payload
    receipt = ctx.ledger.charge(_field(p, 'account'), _amount(p.get('amount')))
    return {'invoice': p.get('invoice'), 'charge': receipt['id']}


def split_charge(job, ctx):
    p = job.payload
    parts = p.get('parts')
    if not isinstance(parts, list) or not parts:
        raise ValueError('split_charge needs a non-empty list of parts')
    checked = [(_field(part, 'account'), _amount(part.get('amount'))) for part in parts]
    charges = [ctx.ledger.charge(account, amount)['id'] for account, amount in checked]
    return {'invoice': p.get('invoice'), 'charges': charges}


def refund(job, ctx):
    p = job.payload
    receipt = ctx.ledger.refund(_field(p, 'account'), _amount(p.get('amount')))
    return {'invoice': p.get('invoice'), 'refund': receipt['id']}


def send_receipt(job, ctx):
    p = job.payload
    amount = _amount(p.get('amount'))
    email = _field(p, 'email')
    receipt = ctx.ledger.charge(_field(p, 'account'), amount)
    body = 'We received %d.%02d for invoice %s. Reference %s.' % (amount // 100, amount % 100, p.get('invoice'),
                                                                   receipt['id'])
    message = ctx.mailer.send(email, 'Your receipt', body)
    return {'invoice': p.get('invoice'), 'charge': receipt['id'], 'message': message['id']}


def notify(job, ctx):
    p = job.payload
    message = ctx.mailer.send(_field(p, 'email'), _field(p, 'subject'), p.get('body', ''))
    return {'message': message['id']}


DEFAULT_HANDLERS = {
    'charge_invoice': charge_invoice,
    'split_charge': split_charge,
    'refund': refund,
    'send_receipt': send_receipt,
    'notify': notify,
}
