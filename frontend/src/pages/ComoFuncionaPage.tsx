import { Link } from 'react-router-dom'
import { isAuthenticated } from '../lib/auth'

/**
 * Página pública que explica o sistema em linguagem simples, com exemplos.
 * Acessível sem login (link no banner de teste e na tela de entrada).
 */

const steps = [
  {
    icon: '📅',
    title: 'O gestor monta o calendário',
    text: 'Define quais dias do mês têm plantão, reserva ou pátio, e quantas vagas cada dia precisa.',
  },
  {
    icon: '✋',
    title: 'Cada perito marca suas preferências',
    text: 'Na sua agenda, você indica "quero trabalhar neste dia" ou "prefiro evitar este dia". É um pedido, não uma garantia.',
  },
  {
    icon: '🧮',
    title: 'O sistema distribui as vagas',
    text: 'Um programa de computador testa milhões de combinações e escolhe a mais justa, respeitando férias, limites e descanso.',
  },
  {
    icon: '📢',
    title: 'A escala é publicada',
    text: 'Todos veem o resultado. Precisou mudar? Você pode propor troca com um colega — o gestor aprova e a escala se atualiza.',
  },
]

const hardRules = [
  { icon: '🏖️', title: 'Férias e licenças', text: 'Quem está de férias, licença ou abono nunca é escalado nesses dias.' },
  { icon: '📏', title: 'Limite mensal', text: 'Ninguém recebe mais plantões do que a cota do seu perfil permite.' },
  { icon: '😴', title: 'Descanso garantido', text: 'Depois de um plantão de 12h, o dia seguinte fica livre. Sempre.' },
  { icon: '🎯', title: 'Só o que você pode fazer', text: 'Cada perito só é escalado nas modalidades liberadas para o seu perfil.' },
]

const saldoExamples = [
  {
    name: 'Ana',
    color: 'bg-emerald-50 border-emerald-200',
    badge: 'text-emerald-700 bg-emerald-100',
    points: '−5 pontos',
    story: 'Pediu para trabalhar no dia 10 e foi atendida. Como foi beneficiada, seu saldo diminui.',
  },
  {
    name: 'Bruno',
    color: 'bg-red-50 border-red-200',
    badge: 'text-red-700 bg-red-100',
    points: '+10 pontos',
    story: 'Pediu para evitar o dia 24, mas não havia outra opção e ele foi escalado. Foi prejudicado — o sistema o compensa nos próximos meses.',
  },
  {
    name: 'Carla',
    color: 'bg-emerald-50 border-emerald-200',
    badge: 'text-emerald-700 bg-emerald-100',
    points: '−10 pontos',
    story: 'Passou o mês inteiro sem nenhuma escala. Ficou "devendo" — tende a ser escalada mais no mês seguinte.',
  },
]

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <h2 className="text-2xl font-bold text-gray-900">{children}</h2>
}

export function ComoFuncionaPage() {
  const backTo = isAuthenticated() ? '/usuario/agenda' : '/login'

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Cabeçalho / hero */}
      <header className="bg-gradient-to-br from-primary-700 via-primary-600 to-blue-500 text-white">
        <div className="mx-auto max-w-4xl px-6 py-12">
          <Link
            to={backTo}
            className="inline-flex items-center gap-1 rounded-lg bg-white/10 px-3 py-1.5 text-sm text-white/90 backdrop-blur hover:bg-white/20"
          >
            ← Voltar
          </Link>
          <div className="mt-6 inline-flex items-center gap-2 rounded-full bg-amber-300 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-amber-950">
            🧪 Versão de teste
          </div>
          <h1 className="mt-4 text-3xl font-bold leading-tight sm:text-4xl">
            Como funciona a distribuição de escalas?
          </h1>
          <p className="mt-4 max-w-2xl text-lg text-blue-100">
            Este sistema organiza os plantões do mês de forma <strong className="text-white">justa e transparente</strong>.
            Aqui você entende, sem tecniquês, o que acontece por trás da sua escala.
          </p>
          <p className="mt-4 max-w-2xl rounded-xl bg-white/10 p-4 text-sm text-blue-50 backdrop-blur">
            <strong className="text-white">Importante:</strong> o sistema está em <strong className="text-white">fase de testes</strong>.
            Ele está sendo avaliado antes da adoção oficial — sua participação e seus relatos de problemas
            ajudam a melhorá-lo. Em caso de divergência, vale a escala oficial divulgada pela gestão.
          </p>
        </div>
      </header>

      <main className="mx-auto max-w-4xl space-y-16 px-6 py-12">
        {/* Passo a passo */}
        <section>
          <SectionTitle>O caminho de uma escala, em 4 passos</SectionTitle>
          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            {steps.map((s, i) => (
              <div key={s.title} className="relative rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
                <div className="flex items-center gap-3">
                  <span className="flex h-9 w-9 items-center justify-center rounded-full bg-primary-600 text-sm font-bold text-white">
                    {i + 1}
                  </span>
                  <span className="text-2xl" aria-hidden="true">{s.icon}</span>
                </div>
                <h3 className="mt-3 font-semibold text-gray-900">{s.title}</h3>
                <p className="mt-1 text-sm leading-relaxed text-gray-600">{s.text}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Não é sorteio */}
        <section className="rounded-2xl border border-primary-100 bg-primary-50 p-8">
          <SectionTitle>Não é sorteio 🎲❌</SectionTitle>
          <p className="mt-3 leading-relaxed text-gray-700">
            A distribuição <strong>não é aleatória</strong> nem depende de escolha manual. Um otimizador
            matemático — o mesmo tipo de tecnologia usada para planejar rotas de entrega e horários de
            hospitais — monta a escala como um <strong>quebra-cabeça</strong>: testa milhões de combinações
            e escolhe a que preenche todas as vagas quebrando o mínimo possível de preferências, sempre
            respeitando as regras obrigatórias.
          </p>
          <p className="mt-3 leading-relaxed text-gray-700">
            E é <strong>auditável</strong>: cada escala gerada fica registrada com as regras e os dados usados,
            e o mesmo cálculo sempre produz o mesmo resultado. Nada de "caixa preta".
          </p>
        </section>

        {/* Regras invioláveis */}
        <section>
          <SectionTitle>Regras que nunca são quebradas</SectionTitle>
          <p className="mt-2 text-gray-600">
            Antes de pensar em preferências, o sistema garante o básico:
          </p>
          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            {hardRules.map((r) => (
              <div key={r.title} className="flex gap-4 rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
                <span className="text-2xl" aria-hidden="true">{r.icon}</span>
                <div>
                  <h3 className="font-semibold text-gray-900">{r.title}</h3>
                  <p className="mt-1 text-sm leading-relaxed text-gray-600">{r.text}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Saldo de justiça */}
        <section>
          <SectionTitle>O "saldo": a memória da justiça ⚖️</SectionTitle>
          <p className="mt-3 leading-relaxed text-gray-700">
            Nem sempre dá para agradar todo mundo no mesmo mês. Por isso, cada perito tem um{' '}
            <strong>saldo de pontos</strong> que registra quem foi prejudicado e quem foi beneficiado —
            e o sistema usa esse histórico para <strong>compensar nos meses seguintes</strong>.
          </p>
          <div className="mt-6 overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-left text-gray-500">
                <tr>
                  <th className="px-5 py-3 font-medium">O que aconteceu no mês</th>
                  <th className="px-5 py-3 font-medium">Efeito no saldo</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 text-gray-700">
                <tr>
                  <td className="px-5 py-3">Foi escalado num dia que pediu para <strong>evitar</strong></td>
                  <td className="px-5 py-3 font-semibold text-red-600">+10 (foi prejudicado)</td>
                </tr>
                <tr>
                  <td className="px-5 py-3">Turno comum, sem preferência envolvida</td>
                  <td className="px-5 py-3 text-gray-500">0</td>
                </tr>
                <tr>
                  <td className="px-5 py-3">Conseguiu um dia que <strong>desejava</strong></td>
                  <td className="px-5 py-3 font-semibold text-emerald-600">−5 (foi beneficiado)</td>
                </tr>
                <tr>
                  <td className="px-5 py-3">Passou o mês <strong>sem nenhuma escala</strong></td>
                  <td className="px-5 py-3 font-semibold text-emerald-600">−10 (foi beneficiado)</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p className="mt-4 text-sm text-gray-600">
            <strong>Saldo alto</strong> = você foi prejudicado → o sistema pega mais leve com você.{' '}
            <strong>Saldo baixo</strong> = você foi poupado → é a sua vez de contribuir mais.
          </p>

          <h3 className="mt-8 text-lg font-semibold text-gray-900">Na prática:</h3>
          <div className="mt-4 grid gap-4 sm:grid-cols-3">
            {saldoExamples.map((e) => (
              <div key={e.name} className={`rounded-xl border p-5 ${e.color}`}>
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-gray-900">{e.name}</span>
                  <span className={`rounded-full px-2 py-0.5 text-xs font-bold ${e.badge}`}>{e.points}</span>
                </div>
                <p className="mt-2 text-sm leading-relaxed text-gray-600">{e.story}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Trocas */}
        <section className="rounded-2xl border border-gray-200 bg-white p-8 shadow-sm">
          <SectionTitle>E se surgir um imprevisto? Troque! 🔁</SectionTitle>
          <p className="mt-3 leading-relaxed text-gray-700">
            A escala publicada não é uma prisão. Veja um exemplo:
          </p>
          <ol className="mt-4 space-y-3">
            {[
              <>O <strong>Davi</strong> foi escalado para o plantão do dia 12, mas surgiu um compromisso.</>,
              <>Pelo sistema, ele propõe uma troca com a <strong>Elisa</strong>, escalada no dia 20.</>,
              <>A Elisa aceita a proposta pela tela de <strong>Trocas</strong>.</>,
              <>O gestor confere e aprova. A escala se atualiza sozinha — e tudo fica registrado.</>,
            ].map((item, i) => (
              <li key={i} className="flex gap-3 text-gray-700">
                <span className="flex h-6 w-6 flex-none items-center justify-center rounded-full bg-primary-100 text-xs font-bold text-primary-700">
                  {i + 1}
                </span>
                <span className="text-sm leading-relaxed sm:text-base">{item}</span>
              </li>
            ))}
          </ol>
          <p className="mt-4 text-sm text-gray-500">
            O sistema só permite trocas válidas: mesma modalidade, sem ferir descanso, limites ou indisponibilidades.
          </p>
        </section>

        {/* Perguntas frequentes */}
        <section>
          <SectionTitle>Perguntas frequentes</SectionTitle>
          <div className="mt-6 space-y-4">
            {[
              {
                q: 'Posso escolher meus dias?',
                a: 'Você pode indicar preferências — dias que deseja e dias que quer evitar. O sistema tenta atender o máximo possível; quando não consegue, seu saldo registra isso e você ganha prioridade nos próximos meses.',
              },
              {
                q: 'Quem decide a escala: uma pessoa ou o computador?',
                a: 'O computador monta a proposta seguindo as regras; o gestor revisa, pode ajustar pontualmente e é quem publica. A responsabilidade final é sempre humana.',
              },
              {
                q: 'Como sei que ninguém foi favorecido?',
                a: 'Três garantias: as regras valem igualmente para todos, o saldo de justiça é público no ranking, e cada versão da escala fica registrada na auditoria — dá para ver o que mudou, quando e por quê.',
              },
              {
                q: 'O que significa "versão de teste"?',
                a: 'O sistema está completo e funcionando, mas em período de avaliação antes de virar a ferramenta oficial. Use normalmente e, se encontrar qualquer comportamento estranho — um dia errado, uma troca que não deveria ser permitida —, avise o gestor: é exatamente para isso que serve esta fase.',
              },
            ].map((f) => (
              <details key={f.q} className="group rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
                <summary className="cursor-pointer list-none font-semibold text-gray-900 marker:hidden">
                  <span className="mr-2 text-primary-600 transition-transform group-open:rotate-90 inline-block">▸</span>
                  {f.q}
                </summary>
                <p className="mt-3 pl-6 text-sm leading-relaxed text-gray-600">{f.a}</p>
              </details>
            ))}
          </div>
        </section>

        {/* CTA final */}
        <section className="rounded-2xl bg-gray-900 p-8 text-center text-white">
          <h2 className="text-2xl font-bold">Pronto para experimentar?</h2>
          <p className="mx-auto mt-2 max-w-xl text-gray-300">
            Entre, marque suas preferências na agenda e veja a distribuição acontecer.
            Sua participação nesta fase de testes ajuda a deixar o sistema pronto para todos.
          </p>
          <Link
            to={backTo}
            className="mt-6 inline-block rounded-lg bg-primary-600 px-6 py-3 font-semibold text-white shadow hover:bg-primary-500"
          >
            {isAuthenticated() ? 'Ir para minha agenda' : 'Entrar no sistema'}
          </Link>
        </section>
      </main>

      <footer className="border-t border-gray-200 bg-white py-6 text-center text-xs text-gray-400">
        Sistema de Gestão de Escalas — versão de teste
      </footer>
    </div>
  )
}
