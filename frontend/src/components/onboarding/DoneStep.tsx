import { useNavigate } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export function DoneStep() {
  const navigate = useNavigate()

  return (
    <Card>
      <CardHeader>
        <CardTitle>You're all set.</CardTitle>
        <CardDescription>
          Your profile is saved locally. Next: crawl some jobs and we'll score them against your CV.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Button onClick={() => navigate('/app')}>Open the app</Button>
      </CardContent>
    </Card>
  )
}
