import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { Dashboard } from '@/pages/Dashboard'

describe('Dashboard', () => {
  it('menampilkan semua kategori dan memfilter lewat pencarian', async () => {
    render(<Dashboard />, { wrapper: MemoryRouter })
    expect(screen.getByText('Riset Operasi (Hillier & Lieberman)')).toBeInTheDocument()

    await userEvent.type(screen.getByPlaceholderText(/Cari metode/), 'simpleks')
    expect(screen.getByText('Metode Simpleks (Simplex Method, Bab 4)')).toBeInTheDocument()
    expect(screen.queryByText('Statistika & Pengolahan Data')).not.toBeInTheDocument()
  })

  it('menampilkan pesan bila tidak ada hasil', async () => {
    render(<Dashboard />, { wrapper: MemoryRouter })
    await userEvent.type(screen.getByPlaceholderText(/Cari metode/), 'zzzz')
    expect(screen.getByText(/Tidak ada metode yang cocok/)).toBeInTheDocument()
  })
})
