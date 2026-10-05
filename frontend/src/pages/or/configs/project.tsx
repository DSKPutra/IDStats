import type { VariantPageConfig } from '@/pages/VariantPage'
import { Theory } from '@/pages/stats/configs/Theory'

const HINT = 'Satu aktivitas per baris: kode | pendahulu (pisahkan koma, “-” bila tidak ada) | '

export const projectConfig: VariantPageConfig = {
  title: 'Manajemen Proyek PERT/CPM (Bab 10)',
  subtitle: 'Diagram AON, ES/EF/LS/LF, slack, jalur kritis, PERT tiga estimasi, crashing via LP, Gantt chart, dan PERT/Cost.',
  exampleModule: 'or',
  variants: [
    {
      id: 'cpm',
      label: 'CPM (jalur kritis)',
      endpoint: '/project/cpm',
      fields: [{ key: 'activities', label: 'Aktivitas', type: 'textarea', required: true, placeholder: 'A | - | 2 | Galian\nB | A | 4 | Fondasi\nC | B | 10', hint: HINT + 'durasi | nama (opsional).' }],
      theory: (
        <Theory formulas={[String.raw`\text{Slack} = LS - ES = LF - EF`]}>
          <p>
            Forward pass menghitung waktu mulai/selesai paling awal; backward pass menghitung waktu paling lambat. Aktivitas dengan
            slack nol membentuk <strong>jalur kritis</strong> — jalur terpanjang yang menentukan waktu penyelesaian proyek.
          </p>
        </Theory>
      ),
    },
    {
      id: 'pert',
      label: 'PERT 3 estimasi',
      endpoint: '/project/pert',
      fields: [
        { key: 'activities', label: 'Aktivitas', type: 'textarea', required: true, placeholder: 'A | - | 1 2 3\nB | A | 2 3.5 8', hint: HINT + 'o m p (optimistis, paling mungkin, pesimistis).' },
        { key: 'deadline', label: 'Tenggat (opsional)', type: 'number', placeholder: '47' },
      ],
      theory: (
        <Theory formulas={[String.raw`\mu = \frac{o + 4m + p}{6},\quad \sigma^2 = \left(\frac{p-o}{6}\right)^2,\quad P(T \le d) \approx \Phi\left(\frac{d - \mu_p}{\sigma_p}\right)`]}>
          <p>
            PERT memodelkan ketidakpastian durasi dengan distribusi beta. Waktu proyek didekati dengan distribusi normal dari
            jalur kritis rata-rata (asumsi: aktivitas saling bebas dan jalur kritis rata-rata selalu terpanjang).
          </p>
        </Theory>
      ),
    },
    {
      id: 'crashing',
      label: 'Crashing (time-cost trade-off)',
      endpoint: '/project/crashing',
      fields: [
        { key: 'activities', label: 'Aktivitas', type: 'textarea', required: true, placeholder: 'A | - | 2 1 180 280', hint: HINT + 'waktu normal, waktu crash, biaya normal, biaya crash.' },
        { key: 'deadline', label: 'Target waktu penyelesaian', type: 'number', required: true, placeholder: '40' },
      ],
      theory: (
        <Theory>
          <p>
            Crashing mempercepat aktivitas dengan biaya tambahan. Model LP (Bab 10.5) memilih pengurangan waktu tiap aktivitas
            yang meminimumkan total biaya crashing sambil memenuhi tenggat. Hanya aktivitas kritis yang layak dipercepat.
          </p>
        </Theory>
      ),
    },
    {
      id: 'pert-cost',
      label: 'PERT/Cost',
      endpoint: '/project/pert-cost',
      fields: [
        { key: 'activities', label: 'Aktivitas', type: 'textarea', required: true, placeholder: 'A | - | 2 180 100 200', hint: HINT + 'durasi, anggaran, % selesai, biaya aktual.' },
        { key: 'current_time', label: 'Waktu pelaporan saat ini', type: 'number', required: true, placeholder: '22' },
      ],
      theory: (
        <Theory>
          <p>
            PERT/Cost membandingkan biaya aktual dengan nilai pekerjaan yang telah selesai (persen selesai × anggaran) untuk
            mendeteksi kelebihan biaya per aktivitas sejak dini. Kurva anggaran kumulatif jadwal ES dan LS memberi batas wajar
            pengeluaran.
          </p>
        </Theory>
      ),
    },
  ],
}
