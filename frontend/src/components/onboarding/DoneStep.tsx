import { useNavigate } from 'react-router-dom'

import { Icon } from '@/components/icons/Icon'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'

export function DoneStep() {
  const navigate = useNavigate()

  return (
    <Card>
      <CardContent className="flex flex-col gap-5 p-8">
        <div>
          <h2 className="mb-1.5 text-[18px] font-semibold tracking-[-0.01em] text-ink">
            You're all set.
          </h2>
          <p className="text-[13px] leading-relaxed text-ink-3">
            Your profile is saved locally on this machine. Nothing was sent anywhere.
          </p>
        </div>

        <div className="rounded-[10px] border border-brand-green-soft bg-brand-green-tint p-4">
          <div className="mb-1.5 flex items-center gap-2">
            <Icon name="sparkle" size={14} className="text-brand-green" />
            <span className="text-[12px] font-semibold text-brand-green">Your agent is ready</span>
          </div>
          <p className="text-[12px] leading-relaxed text-ink-2">
            Next: paste a few job URLs and Hired. will score each one against your CV. You stay in
            control — crawling only runs when you start it.
          </p>
        </div>

        <div>
          <Button onClick={() => navigate('/app')}>
            Open the app <Icon name="arrowRight" size={14} />
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
