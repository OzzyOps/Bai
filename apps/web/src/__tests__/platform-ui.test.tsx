/**
 * Front-end tests for the locked decisions that live in the UI.
 *
 * `pnpm test` previously exited 1 with "no test files found" — the CI web job
 * could not pass, and if it had been made to pass it would have proved nothing.
 * These cover the four promises the interface itself is responsible for:
 *
 *   · money renders in minor units with the right number of decimal places,
 *     for currencies that do not have two (locked decision: never assume 2);
 *   · low confidence never renders as success (the `unknown` token);
 *   · colour is never the only carrier of meaning — the state is in the text;
 *   · an irreversible option says so before it is clicked, not after.
 */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { Can, Confidence, EscalationCard, SourceCitation, exponentFor, formatMoney } from '@bai/ui';

describe('money', () => {
  it('uses the currency exponent, not a hardcoded 2', () => {
    expect(exponentFor('JPY')).toBe(0);
    expect(exponentFor('KWD')).toBe(3);
    expect(exponentFor('GBP')).toBe(2);
    expect(exponentFor('gbp')).toBe(2);
    expect(exponentFor('ZZZ')).toBe(2);
  });

  it('renders JPY with no decimal places', () => {
    // 4,820,000 JPY-minor is ¥4,820,000 — not ¥48,200.00
    const out = formatMoney({ minor: 4_820_000, currency: 'JPY' }, 'ja-JP');
    expect(out).toContain('4,820,000');
    expect(out).not.toContain('.00');
  });

  it('renders KWD with three decimal places', () => {
    const out = formatMoney({ minor: 1_234, currency: 'KWD' }, 'en-GB');
    expect(out).toContain('1.234');
  });

  it('keeps locale and currency independent', () => {
    // A Brazilian tenant holding a USD amount must not be shown BRL.
    const out = formatMoney({ minor: 250_000, currency: 'USD' }, 'pt-BR');
    expect(out).toMatch(/US\$|\$/);
    expect(out).not.toContain('R$');
  });

  it('still renders truthfully for an unknown currency code', () => {
    // Intl accepts any well-formed three-letter code and prints it verbatim,
    // so the amount is correct even for a code it has no symbol for.
    const out = formatMoney({ minor: 100, currency: 'ZZZ' }, 'en-GB');
    expect(out).toContain('1.00');
    expect(out).toContain('ZZZ');
  });

  it('falls back rather than throwing on a malformed code', () => {
    // Intl throws on anything that is not three letters. The catch branch is
    // what stops one bad row taking down the page it appears on.
    const out = formatMoney({ minor: 100, currency: '12' }, 'en-GB');
    expect(out).toBe('1.00 12');
  });
});

describe('confidence', () => {
  it('renders low confidence as "not determined", never as success', () => {
    render(<Confidence confidence={0.41} />);
    const chip = screen.getByText('Not determined').closest('span[data-state]');
    expect(chip).toHaveAttribute('data-state', 'unknown');
  });

  it('separates high from medium at the stated floor', () => {
    const { rerender } = render(<Confidence confidence={0.95} />);
    expect(screen.getByText('High confidence')).toBeInTheDocument();
    rerender(<Confidence confidence={0.7} />);
    expect(screen.getByText('Medium confidence')).toBeInTheDocument();
    rerender(<Confidence confidence={0.69} />);
    expect(screen.getByText('Not determined')).toBeInTheDocument();
  });

  it('spells the state out in text, so colour is never the only signal', () => {
    render(<Confidence confidence={0.2} />);
    // Readable with no stylesheet at all.
    expect(screen.getByText('Not determined')).toBeVisible();
    expect(screen.getByText('20%')).toBeVisible();
  });
});

describe('source citation', () => {
  it('always names the document and the locator', () => {
    render(<SourceCitation documentId="d1" filename="invoice.pdf" locator="p.3" />);
    expect(screen.getByText(/invoice\.pdf · p\.3/)).toBeInTheDocument();
  });

  it('exposes the span when the agent supplied one', async () => {
    const onOpen = vi.fn();
    render(
      <SourceCitation
        documentId="d1"
        filename="invoice.pdf"
        locator="p.3"
        charStart={10}
        charEnd={42}
        onOpen={onOpen}
      />,
    );
    await userEvent.click(screen.getByRole('button', { name: /Open invoice\.pdf at p\.3/ }));
    expect(onOpen).toHaveBeenCalledWith('d1', 10);
  });
});

describe('escalation card', () => {
  const options = [
    { id: 'approve', label: 'Post the payment', consequence: 'Sends £4,182.00', reversible: false },
    { id: 'reject', label: 'Send back', consequence: 'Returns it to the queue', reversible: true },
  ];

  it('warns that an irreversible action cannot be undone, before the click', () => {
    render(
      <EscalationCard
        title="Approve payment?"
        reason="Confidence below the threshold"
        confidence={0.41}
        irreversible
        options={options}
        onResolve={vi.fn()}
      />,
    );
    expect(screen.getByRole('note')).toHaveTextContent(/cannot be undone/i);
    expect(screen.getByText(/Sends £4,182\.00 · cannot be undone/)).toBeInTheDocument();
  });

  it('does not disable or hide the irreversible option behind a friendlier default', () => {
    render(
      <EscalationCard
        title="Approve payment?"
        reason="Confidence below the threshold"
        irreversible
        options={options}
        onResolve={vi.fn()}
      />,
    );
    const buttons = screen.getAllByRole('button');
    expect(buttons).toHaveLength(2);
    buttons.forEach((b) => { expect(b).toBeEnabled(); });
  });

  it('blocks every option while a resolution is in flight', () => {
    render(
      <EscalationCard
        title="Approve payment?"
        reason="Confidence below the threshold"
        irreversible
        options={options}
        onResolve={vi.fn()}
        busy
      />,
    );
    screen.getAllByRole('button').forEach((b) => { expect(b).toBeDisabled(); });
  });
});

describe('Can', () => {
  it('renders children only when the permission is held', () => {
    const { rerender } = render(
      <Can permission="record.write" permissions={['record.read']} fallback={<span>no</span>}>
        <span>yes</span>
      </Can>,
    );
    expect(screen.getByText('no')).toBeInTheDocument();

    rerender(
      <Can permission="record.write" permissions={['record.read', 'record.write']}>
        <span>yes</span>
      </Can>,
    );
    expect(screen.getByText('yes')).toBeInTheDocument();
  });
});
