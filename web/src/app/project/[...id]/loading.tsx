import { Loader2 } from 'lucide-react'

export default function Loading() {
  return (
    <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
            <div className="flex justify-center mb-4">
            <Loader2 className="text-pink-600 h-12 w-12 animate-spin" />
            </div>
            <p className="text-gray-600">Loading Project...</p>
        </div>
    </div>
  )
}