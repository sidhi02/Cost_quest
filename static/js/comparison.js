'use strict';
(() => {
  const select = document.getElementById('cq-sort');
  const list = document.getElementById('cq-offers');
  const retailer = document.getElementById('cq-store-filter');
  const count = document.getElementById('cq-filter-count');
  const empty = document.getElementById('cq-filter-empty');
  if (!list || !select) return;
  const update = () => {
    const cards = [...list.querySelectorAll('.cq-offer')];
    cards.sort((a, b) => {
      if (select.value === 'retailer') return a.dataset.retailer.localeCompare(b.dataset.retailer) || Number(a.dataset.price) - Number(b.dataset.price);
      return (Number(a.dataset.price) - Number(b.dataset.price)) * (select.value === 'high' ? -1 : 1);
    });
    cards.forEach(card => list.appendChild(card));
    let visible = 0;
    cards.forEach(card => {
      const match = !retailer || retailer.value === 'all' || card.dataset.retailer === retailer.value;
      card.hidden = !match;
      if (match) visible++;
    });
    if (count) count.textContent = visible + ' verified ' + (visible === 1 ? 'offer' : 'offers') + ' shown';
    if (empty) empty.hidden = visible > 0;
  };
  select.addEventListener('change', update);
  if (retailer) retailer.addEventListener('change', update);
  update();
})();
