// frontend/src/lib/categories.test.ts
import { describe, expect, it } from 'vitest';
import { CATEGORIES, CATEGORY_IDS, POINT_CATEGORIES } from './categories';

describe('category catalogue', () => {
  it('covers all seven categories with unique layers', () => {
    expect(CATEGORY_IDS).toHaveLength(7);
    const layerIds = CATEGORY_IDS.map((c) => CATEGORIES[c].layerId);
    expect(new Set(layerIds).size).toBe(7);
  });

  it('draws every category but satellites as points', () => {
    expect(POINT_CATEGORIES).not.toContain('satellite');
    expect(POINT_CATEGORIES).toHaveLength(6);
  });
});
