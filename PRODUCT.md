# Сверка данных
<!-- impeccable:product-schema 1 -->

## Platform
web

## Stack
React + TypeScript required by fullstack.pdf v2.2. Vite for this frontend prototype.

## Users
People checking the transfer of monthly charges from 1C to PostgreSQL.

## Product Purpose
Show verifiable counts, sums and record-level differences for a selected month.

## Capabilities and Constraints
One page: month, import, reconciliation, pending/error/no-difference states and differences table.
Current scope is frontend only. All operations are explicitly simulated; no real integration or agent is claimed.
Fixture data follows the previously reviewed CONTRACT.md. Accounts and payments are imported; charges are reconciled.
No chat, authentication, extra pages, task queue or payment reconciliation.

## Brand Commitments
User requested skills used for Cloud Music, but explicitly rejected its visual style. Use a neutral operational interface, simple code and Russian comments.

## Evidence on Hand
User supplied /Users/konstantinovmihail/Downloads/fullstack.pdf, version 2.2.
Cloud Music DESIGN.md and admin-home.css were inspected read-only.

## Product Principles
Exact amounts. Explicit source failures. Visible demo boundary. One future backend owns reconciliation.
