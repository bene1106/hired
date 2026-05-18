import { useNavigate } from 'react-router-dom'

import { Icon } from '@/components/icons/Icon'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'

export function WelcomeStep() {
  const navigate = useNavigate()

  return (
    <Card>
      <CardContent className="flex flex-col gap-5 p-8">
        <div>
          <h2 className="mb-1.5 text-[18px] font-semibold tracking-[-0.01em] text-ink">
            Welcome to Hired.
          </h2>
          <p className="text-[13px] leading-relaxed text-ink-3">
            A local-first AI career agent: it finds jobs, tailors your applications, and preps you
            for interviews. Your CV, jobs, applications, and API keys never leave this machine.
          </p>
        </div>

        <div className="flex flex-col gap-2 text-[13px] text-ink-2">
          <p>Four short steps to get going:</p>
          <ol className="flex flex-col gap-1 pl-4 text-ink-3">
            <li>1 — Pick an LLM provider</li>
            <li>2 — Upload your CV</li>
            <li>3 — Confirm what you're looking for</li>
            <li>4 — You're ready to crawl jobs</li>
          </ol>
        </div>

        <div>
          <Button onClick={() => navigate('/onboarding/provider')}>
            Get started <Icon name="arrowRight" size={14} />
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
