from ledgerbook import Ledger


def march():
    """A small ledger used by several tests: two accounts, February and March."""
    ledger = Ledger()
    ledger.add('2024-02-27', 'checking', 'opening', 100000, 'opening balance')
    ledger.add('2024-02-28', 'savings', 'opening', 500000, 'opening balance')
    ledger.add('2024-03-01', 'checking', 'salary', 250000, 'March pay')
    ledger.add('2024-03-02', 'checking', 'groceries', -4599, 'market; bread and cheese')
    ledger.add('2024-03-09', 'checking', 'groceries', -12000, 'big shop')
    ledger.add('2024-03-15', 'checking', 'rent', -90000, 'rent; March')
    ledger.add('2024-03-20', 'checking', 'groceries', 1500, 'refund')
    ledger.add('2024-03-31', 'savings', 'transfer', 50000, 'monthly saving')
    ledger.add('2024-03-31', 'checking', 'transfer', -50000, 'monthly saving')
    ledger.add('2024-04-02', 'checking', 'groceries', -3000, 'April')
    return ledger
