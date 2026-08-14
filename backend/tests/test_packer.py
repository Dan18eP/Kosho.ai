import pytest
from app.core.provider_spec import ProviderSpec
from app.core.token_counter import TokenCounter
from app.modules.debate.retrieval import Quote
from app.modules.optimizer.packer import Packer, PackingError
from app.modules.optimizer.receipt import ReceiptBuilder

QUOTES = [
    Quote(phrase="Knowledge is power.", author="Francis Bacon"),
    Quote(phrase="The unexamined life is not worth living.", author="Socrates"),
    Quote(
        phrase="Imagination is more important than knowledge.", author="Albert Einstein"
    ),
    Quote(
        phrase="Life is what happens to us while we are making other plans.",
        author="Allen Saunders",
    ),
    Quote(
        phrase="It is during our darkest moments that we must focus to see the light.",
        author="Aristotle Onassis",
    ),
    Quote(
        phrase="I have not failed. I have just found 10,000 ways that will not work.",
        author="Thomas Edison",
    ),
    Quote(
        phrase="The best way to predict the future is to invent it.", author="Alan Kay"
    ),
    Quote(phrase="Everything you can imagine is real.", author="Pablo Picasso"),
]


@pytest.fixture()
def packer():
    return Packer(TokenCounter())


def _spec(max_tokens=200, max_chars=None):
    return ProviderSpec(
        max_tokens_per_request=max_tokens,
        max_chars_per_request=max_chars,
        system_prompt_tokens=10,
        json_format_overhead=5,
    )


class TestPacker:
    def test_never_exceeds_limit(self, packer):
        spec = _spec(max_tokens=120)
        batches = packer.pack(QUOTES, spec)
        for b in batches:
            total = spec.system_prompt_tokens + spec.json_format_overhead
            total += b.input_tokens + b.output_tokens
            assert total <= spec.max_tokens_per_request

    def test_all_phrases_covered_once(self, packer):
        batches = packer.pack(QUOTES, _spec(max_tokens=120))
        indices = [i.index for b in batches for i in b.items]
        assert sorted(indices) == list(range(len(QUOTES)))

    def test_multiple_batches_for_small_limit(self, packer):
        batches = packer.pack(QUOTES, _spec(max_tokens=150))
        assert len(batches) >= 2

    def test_single_batch_for_large_limit(self, packer):
        batches = packer.pack(QUOTES, _spec(max_tokens=2000))
        assert len(batches) == 1

    def test_respects_chars_limit(self, packer):
        spec = _spec(max_tokens=2000, max_chars=120)
        batches = packer.pack(QUOTES, spec)
        for b in batches:
            assert b.chars <= spec.max_chars_per_request

    def test_sorted_desc_by_cost(self, packer):
        batches = packer.pack(QUOTES, _spec(max_tokens=2000))
        first = batches[0]
        costs = [i.cost for i in first.items]
        # FFD coloca el mayor primero; dentro del primer lote el mayor coste va primero.
        assert costs == sorted(costs, reverse=True)

    def test_raises_when_phrase_alone_exceeds(self, packer):
        huge = Quote(phrase="A" * 5000, author="X")
        spec = _spec(max_tokens=50)
        with pytest.raises(PackingError):
            packer.pack([huge], spec)

    def test_empty_list(self, packer):
        assert packer.pack([], _spec()) == []


class TestReceipt:
    def test_receipt_totals(self, packer):
        spec = _spec(max_tokens=120)
        batches = packer.pack(QUOTES, spec)
        receipt = ReceiptBuilder(spec).build(batches)
        assert receipt.total_requests == len(batches)
        assert (
            receipt.total_tokens
            == receipt.total_input_tokens + receipt.total_output_tokens
        )
        assert sum(b.phrase_count for b in receipt.batches) == len(QUOTES)

    def test_receipt_uses_actual_output_tokens(self, packer):
        spec = _spec(max_tokens=120)
        batches = packer.pack(QUOTES, spec)
        actual = [[30] * len(b.items) for b in batches]
        receipt = ReceiptBuilder(spec).build(batches, actual_output_tokens=actual)
        assert all(b.output_tokens == 30 * b.phrase_count for b in receipt.batches)

    def test_receipt_cost_nonnegative(self, packer):
        spec = _spec(max_tokens=120)
        batches = packer.pack(QUOTES, spec)
        receipt = ReceiptBuilder(spec).build(batches)
        assert receipt.total_cost >= 0
