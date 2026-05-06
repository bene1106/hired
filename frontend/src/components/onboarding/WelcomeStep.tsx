import { useNavigate } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export function WelcomeStep() {
  const navigate = useNavigate()

  return (
    <Card>
      <CardHeader>
        <CardTitle>Welcome to Hired.</CardTitle>
        <CardDescription>
          Local-first AI for finding jobs, tailoring applications, and prepping for
          interviews. Your data never leaves this machine.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <p className="text-sm text-muted-foreground">
          We'll set you up in four short steps: pick an LLM provider, upload your CV,
          confirm what you're looking for, and you're ready to crawl jobs.
        </p>
        <div>
          <Button onClick={() => navigate('/onboarding/provider')}>Get started</Button>
        </div>
      </CardContent>
    </Card>
  )
}
