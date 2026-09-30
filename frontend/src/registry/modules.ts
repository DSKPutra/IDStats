import registry from '@shared/modules.json'

export interface MethodInfo {
  id: string
  title: string
  phase: number
  available?: boolean
}

export interface CategoryInfo {
  id: string
  title: string
  description: string
  methods: MethodInfo[]
}

export const categories: CategoryInfo[] = registry.categories

export function methodPath(categoryId: string, methodId: string) {
  return `/${categoryId}/${methodId}`
}

export function findMethod(categoryId: string, methodId: string) {
  const category = categories.find((c) => c.id === categoryId)
  const method = category?.methods.find((m) => m.id === methodId)
  return category && method ? { category, method } : undefined
}

export function searchMethods(query: string) {
  const q = query.trim().toLowerCase()
  return categories
    .map((c) => ({
      ...c,
      methods: q ? c.methods.filter((m) => `${m.title} ${m.id} ${c.title}`.toLowerCase().includes(q)) : c.methods,
    }))
    .filter((c) => c.methods.length > 0)
}
