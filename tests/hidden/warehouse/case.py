"""Frozen traps for the larger warehouse-ledger case."""
CHANGE = 'warehouse-ledger'
MODULE = 'warehouse'
TRAP_GROUPS = {'ExistingApi': 1, 'QuantityValidation': 2, 'CanonicalItems': 3,
               'ReceiptReplay': 2, 'ReceiptConflict': 2, 'ExpiryCapacity': 3,
               'DetachedState': 4, 'TerminalIds': 4, 'ShipRetry': 5,
               'TransferReservations': 6, 'BundleExpansion': 7,
               'SnapshotHistory': 8, 'SnapshotValidation': 8,
               'BatchAtomicity': 9, 'BatchReplay': 9}
TRAPS = ['SpecScenarios', *TRAP_GROUPS]
MUTANTS = {
 'ExistingApi': ('SCHEMA_VERSION = 1', 'SCHEMA_VERSION = 2'),
 'QuantityValidation': ('type(qty) is not int or qty <= 0', 'not isinstance(qty, int) or qty <= 0'),
 'CanonicalItems': ('result[name] = result.get(name, 0) + _quantity(qty)', 'result[name] = _quantity(qty)'),
 'ReceiptReplay': ('        return result\n    result["events"][event] = args', '        result["stock"][key] += qty\n        return result\n    result["events"][event] = args'),
 'ReceiptConflict': ('if result["events"][event] != args:', 'if False:'),
 'ExpiryCapacity': ('and o["expires"] > now)', 'and o["expires"] >= now)'),
 'DetachedState': ('def sweep(state, now):\n    result = deepcopy(state)', 'def sweep(state, now):\n    result = dict(state)'),
 'TerminalIds': ('if order in state["orders"] or expires <= now:', 'if (order in state["orders"] and state["orders"][order]["status"] == "active") or expires <= now:'),
 'ShipRetry': ('if record["status"] == "shipped":\n        return result', 'if record["status"] == "shipped":\n        for sku, qty in record["items"].items():\n            result["stock"][stock_key(record["site"], sku)] -= qty\n        return result'),
 'TransferReservations': ('if _available(state, source, sku, now) < qty:', 'if state["stock"].get(stock_key(source, sku), 0) < qty:'),
 'BundleExpansion': ('expanded[sku] = expanded.get(sku, 0) + qty * count', 'expanded[sku] = qty * count'),
 'SnapshotHistory': ('result = deepcopy(state)\n        result["stock"] = {}', 'result = deepcopy(state)\n        result["events"] = {}\n        result["stock"] = {}'),
 'SnapshotValidation': ('if type(qty) is not int or qty < 0:', 'if False:'),
 'BatchAtomicity': ('        result = operations[op](result, **args)', '        result = operations[op](result, **args)\n        state.clear()\n        state.update(deepcopy(result))'),
 'BatchReplay': ('        result = operations[op](result, **args)', '        if op == "receive":\n            args["event"] = str(len(result["events"])) + ":" + args["event"]\n        result = operations[op](result, **args)'),
}
UNPROVABLE_TASKS = ['10.1', '10.2']
