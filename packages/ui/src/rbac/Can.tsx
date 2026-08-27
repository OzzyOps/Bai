import type { ReactNode } from 'react';

export type Permission = string;

export interface CanProps {
  permission: Permission;
  permissions: readonly Permission[];
  children: ReactNode;
  /** Shown instead of the children. Prefer explaining over hiding silently. */
  fallback?: ReactNode | undefined;
}

/**
 * Conditional rendering by permission.
 *
 * This is presentation only. It is NOT an authorisation boundary — RLS in
 * Postgres is. Hiding a button the API would refuse anyway is a courtesy to the
 * user, never a security control, and must never be treated as one.
 */
export function Can({ permission, permissions, children, fallback = null }: CanProps) {
  return <>{permissions.includes(permission) ? children : fallback}</>;
}
