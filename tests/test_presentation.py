from services.presentation import prepare_comparison


def offer(price, colour, retailer='Croma', key='model-128', confidence='high', url=None):
    return dict(price=price, retailer=retailer, product_key=key,
                name='Phone', match_confidence=confidence,
                availability='Available', attributes={'color': colour},
                url=url or 'https://example.com/' + colour)


def test_colour_grouping_only_at_same_price_and_store():
    rows, review, best = prepare_comparison([
        offer(100, 'Blue'), offer(100, 'Black'), offer(110, 'Pink'),
        offer(100, 'Blue', retailer='Amazon'), offer(100, 'Blue', key='model-256')])
    assert len(rows) == 4
    assert any(set(r['colour_options']) == {'Blue', 'Black'} for r in rows)
    assert best == 100
    assert not review


def test_review_not_ranked_and_lowest_first():
    rows, review, best = prepare_comparison([
        offer(50, 'Blue', confidence='review'), offer(150, 'Black'), offer(120, 'Pink')])
    assert [r['price'] for r in rows] == [120, 150]
    assert len(review) == 1 and best == 120
    assert rows[0]['featured_best'] and not rows[1]['featured_best']


def test_unverified_never_wins():
    item = offer(10, 'Blue')
    item['unverified_attributes'] = ['storage']
    rows, review, best = prepare_comparison([item])
    assert not rows and len(review) == 1 and best is None


def test_unavailable_and_unknown_confidence_cannot_win():
    unavailable=offer(1,'Green')
    unavailable['availability']='Not available'
    unknown=offer(2,'Blue',confidence='')
    verified=offer(150,'Black')
    shown,review,best=prepare_comparison([unavailable,unknown,verified])
    assert len(shown)==1 and shown[0]['price']==150
    assert len(review)==2 and best==150


def test_invalid_and_non_finite_prices_never_win():
    invalid=offer(float('nan'),'Black')
    negative=offer(-25,'Blue')
    shown,review,best=prepare_comparison([invalid,negative,offer(200,'Green')])
    assert len(shown)==1 and len(review)==2 and best==200
