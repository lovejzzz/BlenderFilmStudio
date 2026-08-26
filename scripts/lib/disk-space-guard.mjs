import { statfs } from 'node:fs/promises';

export const GIB = 1024n ** 3n;
export const DEFAULT_RESERVE_GIB = 100;
export const DEFAULT_PROJECTED_WRITE_GIB = 20;

function requireNonNegativeBigInt(value, label) {
  if (typeof value !== 'bigint' || value < 0n) {
    throw new Error(`${label} must be a non-negative bigint`);
  }
}

export function gibToBytes(value, label = 'GiB value') {
  const numeric = Number(value);
  if (!Number.isFinite(numeric) || numeric < 0) {
    throw new Error(`${label} must be a non-negative number`);
  }
  return BigInt(Math.ceil(numeric * Number(GIB)));
}

export function evaluateDiskSpace({
  availableBytes,
  capacityBytes,
  reserveBytes,
  projectedWriteBytes,
  target,
}) {
  requireNonNegativeBigInt(availableBytes, 'availableBytes');
  requireNonNegativeBigInt(capacityBytes, 'capacityBytes');
  requireNonNegativeBigInt(reserveBytes, 'reserveBytes');
  requireNonNegativeBigInt(projectedWriteBytes, 'projectedWriteBytes');

  const freeAfterProjectedBytes = availableBytes - projectedWriteBytes;
  const status = freeAfterProjectedBytes >= reserveBytes ? 'PASS' : 'BLOCKED';

  return {
    documentType: 'BFS_DISK_SPACE_GUARD_RESULT',
    version: '0.1.0',
    status,
    target,
    capacityBytes: capacityBytes.toString(),
    availableBytes: availableBytes.toString(),
    reserveBytes: reserveBytes.toString(),
    projectedWriteBytes: projectedWriteBytes.toString(),
    freeAfterProjectedBytes: freeAfterProjectedBytes.toString(),
    reason: status === 'PASS' ? null : 'FREE_AFTER_PROJECTED_WRITE_BELOW_RESERVE',
    policy: {
      automaticDeletion: false,
      overrideRequiresExplicitEnvironment: true,
    },
  };
}

export async function checkDiskSpace({
  target = process.cwd(),
  reserveGiB = process.env.BFS_DISK_RESERVE_GIB ?? DEFAULT_RESERVE_GIB,
  projectedWriteGiB = process.env.BFS_PROJECTED_WRITE_GIB ?? DEFAULT_PROJECTED_WRITE_GIB,
} = {}) {
  const filesystem = await statfs(target, { bigint: true });
  return evaluateDiskSpace({
    availableBytes: filesystem.bavail * filesystem.bsize,
    capacityBytes: filesystem.blocks * filesystem.bsize,
    reserveBytes: gibToBytes(reserveGiB, 'reserveGiB'),
    projectedWriteBytes: gibToBytes(projectedWriteGiB, 'projectedWriteGiB'),
    target,
  });
}
