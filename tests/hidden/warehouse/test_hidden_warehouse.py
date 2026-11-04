import copy
import json
import unittest
import warehouse as w


def stocked():
    return w.receive(w.new_state(), 'north', 'a', 10, 'e1')


def reserved():
    return w.reserve(stocked(), 'o1', 'north', {'a': 4}, 10, 1)


class SpecScenarios(unittest.TestCase):
    def test_workflow(self):
        state = w.ship(reserved(), 'o1', 2)
        self.assertEqual(state['stock']['NORTH:A'], 6)
        state = w.transfer(state, 'north', 'south', 'a', 3, 2)
        self.assertEqual(state['stock']['SOUTH:A'], 3)
        self.assertEqual(w.load_state(w.dump_state(w.new_state())), w.new_state())
        self.assertEqual(w.cancel(reserved(), 'o1')['orders']['o1']['status'], 'cancelled')
        self.assertEqual(w.reserve_bundle(stocked(), 'kit', 'north', {'k': 1}, {'k': {'A': 2}}, 20, 1)['orders']['kit']['items'], {'A': 2})


class ExistingApi(unittest.TestCase):
    def test_api(self):
        self.assertEqual(w.SCHEMA_VERSION, 1)
        self.assertEqual(w.stock_key(' north ', ' a '), 'NORTH:A')


class QuantityValidation(unittest.TestCase):
    def test_bool(self):
        with self.assertRaises(ValueError):
            w.receive(w.new_state(), 'n', 'a', True, 'e')


class CanonicalItems(unittest.TestCase):
    def test_duplicates(self):
        state = w.reserve(stocked(), 'o', 'north', {'a': 2, ' A ': 3}, 10, 1)
        self.assertEqual(state['orders']['o']['items'], {'A': 5})


class ReceiptReplay(unittest.TestCase):
    def test_replay(self):
        self.assertEqual(w.receive(stocked(), ' NORTH ', ' A ', 10, 'e1'), stocked())


class ReceiptConflict(unittest.TestCase):
    def test_conflict(self):
        with self.assertRaises(ValueError):
            w.receive(stocked(), 'north', 'a', 11, 'e1')


class ExpiryCapacity(unittest.TestCase):
    def test_boundary(self):
        state = w.reserve(reserved(), 'o2', 'north', {'a': 10}, 20, 10)
        self.assertEqual(state['orders']['o2']['items'], {'A': 10})


class DetachedState(unittest.TestCase):
    def test_no_alias(self):
        state = reserved()
        saved = copy.deepcopy(state)
        result = w.sweep(state, 2)
        result['orders']['o1']['items']['A'] = 999
        self.assertEqual(state, saved)


class TerminalIds(unittest.TestCase):
    def test_reuse(self):
        state = w.cancel(reserved(), 'o1')
        with self.assertRaises(ValueError):
            w.reserve(state, 'o1', 'north', {'a': 1}, 20, 2)


class ShipRetry(unittest.TestCase):
    def test_retry(self):
        state = w.ship(reserved(), 'o1', 2)
        self.assertEqual(w.ship(state, 'o1', 50), state)


class TransferReservations(unittest.TestCase):
    def test_held_stock(self):
        with self.assertRaises(ValueError):
            w.transfer(reserved(), 'north', 'south', 'a', 7, 2)


class BundleExpansion(unittest.TestCase):
    def test_shared_components(self):
        state = w.reserve_bundle(stocked(), 'o', 'north', {'k': 2, 'j': 1},
                                 {'k': {'a': 2}, 'j': {' A ': 1}}, 20, 1)
        self.assertEqual(state['orders']['o']['items'], {'A': 5})


class SnapshotHistory(unittest.TestCase):
    def test_reloaded_replay(self):
        state = w.ship(reserved(), 'o1', 2)
        restored = w.load_state(w.dump_state(state))
        self.assertEqual(w.receive(restored, 'north', 'a', 10, 'e1'), state)
        self.assertEqual(w.ship(restored, 'o1', 100), state)


class SnapshotValidation(unittest.TestCase):
    def test_invalid_stock(self):
        for qty in (-1, True):
            state = w.new_state()
            state['stock']['NORTH:A'] = qty
            with self.assertRaises(ValueError):
                w.load_state(json.dumps({'version': 1, 'state': state}))


class BatchAtomicity(unittest.TestCase):
    def test_rollback(self):
        state = stocked()
        saved = copy.deepcopy(state)
        commands = [{'op': 'receive', 'site': 'north', 'sku': 'a', 'qty': 3, 'event': 'e2'},
                    {'op': 'transfer', 'source': 'north', 'target': 'south', 'sku': 'a', 'qty': 50}]
        with self.assertRaises(ValueError):
            w.apply_batch(state, commands, 2)
        self.assertEqual(state, saved)


class BatchReplay(unittest.TestCase):
    def test_ordered_replay(self):
        command = {'op': 'receive', 'site': 'north', 'sku': 'a', 'qty': 10, 'event': 'e1'}
        state = w.apply_batch(w.new_state(), [command, command,
                    {'op': 'reserve', 'order': 'o', 'site': 'north', 'items': {'a': 10}, 'expires': 20},
                    {'op': 'ship', 'order': 'o'}], 2)
        self.assertEqual(state['stock']['NORTH:A'], 0)
        self.assertEqual(state['orders']['o']['status'], 'shipped')
