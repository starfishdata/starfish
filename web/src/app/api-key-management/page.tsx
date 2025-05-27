'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { useToast } from '@/components/ui/use-toast';
import { Copy, Plus, Trash2, ChevronRight } from 'lucide-react';
import { useRouter } from 'next/navigation';

export default function ApiKeyManagement() {
  const [apiKeys, setApiKeys] = useState<any[]>([]);
  const [newKeyName, setNewKeyName] = useState('');
  const [newKeyDescription, setNewKeyDescription] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [selectedKeyId, setSelectedKeyId] = useState<string | null>(null);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showKeyDialog, setShowKeyDialog] = useState(false);
  const [newlyCreatedKey, setNewlyCreatedKey] = useState<string | null>(null);
  const { toast } = useToast();
  const router = useRouter();

  // Fetch API keys when the component mounts
  useEffect(() => {
    handleListApiKeys();
  }, []);

  // Function to create a new API key
  const handleCreateApiKey = async () => {
    if (!newKeyName) {
      toast({
        title: 'Error',
        description: 'Please enter a name for the API key',
        variant: 'destructive',
      });
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch('/api/api-key-management/create', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: newKeyName,
          description: newKeyDescription,
        }),
      });

      const data = await response.json();
      
      if (response.ok) {
        // Store the API key and show the dialog
        setNewlyCreatedKey(data.apiKey);
        
        // Add the new key to the list without refreshing
        const newKey = {
          id: data.keyId || Date.now().toString(),
          name: newKeyName,
          description: newKeyDescription,
          createdDate: new Date().toISOString(),
        };
        
        setApiKeys(prevKeys => [newKey, ...prevKeys]);
        
        // Reset form and close create dialog
        setNewKeyName('');
        setNewKeyDescription('');
        setShowCreateDialog(false);
        
        // Show the key display dialog
        setShowKeyDialog(true);
      } else {
        toast({
          title: 'Error',
          description: data.error || 'Failed to create API key',
          variant: 'destructive',
        });
      }
    } catch (error) {
      console.error('Error creating API key:', error);
      toast({
        title: 'Error',
        description: 'An unexpected error occurred',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  // Function to copy API key to clipboard
  const copyApiKeyToClipboard = () => {
    if (newlyCreatedKey) {
      navigator.clipboard.writeText(newlyCreatedKey);
      toast({
        title: 'Copied',
        description: 'API key copied to clipboard',
      });
    }
  };

  // Format date and time for display
  const formatDateTime = (dateString: string) => {
    if (!dateString) return 'Unknown';
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  // Clean the API key name by removing the UUID prefix
  const cleanApiKeyName = (name: string) => {
    // If the name contains a UUID pattern (8-4-4-4-12 format), remove it and any trailing hyphen
    const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}-?/i;
    return name.replace(uuidPattern, '').trim();
  };

  // Function to list API keys
  const handleListApiKeys = async () => {
    setIsLoading(true);
    try {
      const response = await fetch('/api/api-key-management/list', {
        method: 'GET',
      });

      const data = await response.json();
      
      if (response.ok) {
        // Make sure we have items, even if the response doesn't include them
        const items = data.items || [];
        setApiKeys(items);
      } else {
        toast({
          title: 'Error',
          description: data.error || 'Failed to list API keys',
          variant: 'destructive',
        });
        // Set empty array to avoid undefined errors
        setApiKeys([]);
      }
    } catch (error) {
      console.error('Error listing API keys:', error);
      toast({
        title: 'Error',
        description: 'An unexpected error occurred',
        variant: 'destructive',
      });
      // Set empty array to avoid undefined errors
      setApiKeys([]);
    } finally {
      setIsLoading(false);
    }
  };

  // Function to delete an API key
  const handleDeleteApiKey = async () => {
    if (!selectedKeyId) {
      toast({
        title: 'Error',
        description: 'Please select an API key to delete',
        variant: 'destructive',
      });
      return;
    }

    setIsDeleting(true);
    
    try {
      const response = await fetch('/api/api-key-management/delete', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          keyId: selectedKeyId,
        }),
      });

      const data = await response.json();
      
      if (response.ok) {
        // Only remove the key from the UI after successful deletion
        setApiKeys(prevKeys => prevKeys.filter(key => key.id !== selectedKeyId));
        setSelectedKeyId(null);
        
        toast({
          title: 'Success',
          description: 'API key deleted successfully',
        });
      } else {
        toast({
          title: 'Error',
          description: data.error || 'Failed to delete API key',
          variant: 'destructive',
        });
      }
    } catch (error) {
      console.error('Error deleting API key:', error);
      toast({
        title: 'Error',
        description: 'An unexpected error occurred',
        variant: 'destructive',
      });
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-4 sm:py-8">
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4 mb-6">
        <h1 className="text-2xl sm:text-3xl font-bold">API Key Management</h1>
        <Button 
          onClick={() => setShowCreateDialog(true)}
          className="bg-pink-600 hover:bg-pink-700 text-white w-full sm:w-auto"
        >
          <Plus className="mr-2 h-4 w-4" />
          Create New API Key
        </Button>
      </div>

      {/* API Key List */}
      <Card>
        <CardHeader>
          <CardTitle>Your API Keys</CardTitle>
          <CardDescription>
            Manage your API keys for accessing the Starfish API
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-pink-600"></div>
            </div>
          ) : (
            <div className="space-y-4">
              {apiKeys.length === 0 ? (
                <p className="text-center text-muted-foreground py-4">
                  No API keys found. Create one to get started.
                </p>
              ) : (
                <div className="space-y-2">
                  {apiKeys.map((key) => (
                    <div 
                      key={key.id} 
                      className={`group border border-gray-200 rounded-lg p-3 sm:p-4 transition-all duration-200 ease-in-out hover:shadow-md hover:border-pink-200 bg-white cursor-pointer ${
                        selectedKeyId === key.id ? 'border-pink-500 bg-pink-50' : ''
                      }`}
                      onClick={() => setSelectedKeyId(key.id)}
                    >
                      <h3 className="text-base sm:text-lg font-semibold mb-2 text-gray-900 group-hover:text-pink-600">{cleanApiKeyName(key.name)}</h3>
                      <p className="text-sm sm:text-base text-gray-600 mb-2 sm:mb-4">{key.description || 'No description'}</p>
                      <div className="text-xs text-gray-500">
                        Created: {formatDateTime(key.createdDate)}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </CardContent>
        <CardFooter className="flex flex-col sm:flex-row gap-2 sm:gap-0 sm:justify-between">
          <Button 
            variant="destructive" 
            disabled={!selectedKeyId || isLoading || isDeleting}
            onClick={handleDeleteApiKey}
            className="w-full sm:w-auto"
          >
            {isDeleting ? (
              <>
                <div className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-pink-600 border-t-transparent"></div>
                Deleting key...
              </>
            ) : (
              <>
                <Trash2 className="mr-2 h-4 w-4" />
                Delete Selected Key
              </>
            )}
          </Button>
          <Button 
            variant="outline" 
            onClick={handleListApiKeys}
            disabled={isLoading}
            className="w-full sm:w-auto"
          >
            Refresh List
          </Button>
        </CardFooter>
      </Card>

      {/* Create API Key Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Create New API Key</DialogTitle>
            <DialogDescription>
              Create a new API key to access the Starfish API
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <label htmlFor="keyName" className="text-sm font-medium">
                Key Name
              </label>
              <Input
                id="keyName"
                placeholder="e.g., Production API Key"
                value={newKeyName}
                onChange={(e) => setNewKeyName(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label htmlFor="keyDescription" className="text-sm font-medium">
                Description (Optional)
              </label>
              <Textarea
                id="keyDescription"
                placeholder="Describe what this API key is used for"
                value={newKeyDescription}
                onChange={(e) => setNewKeyDescription(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter className="flex flex-col sm:flex-row gap-2 sm:gap-0">
            <Button 
              variant="outline" 
              onClick={() => setShowCreateDialog(false)}
              className="w-full sm:w-auto"
            >
              Cancel
            </Button>
            <Button 
              onClick={handleCreateApiKey} 
              disabled={isLoading || !newKeyName}
              className="bg-pink-600 hover:bg-pink-700 text-white w-full sm:w-auto"
            >
              {isLoading ? 'Creating key...' : 'Create API Key'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* API Key Display Dialog */}
      <Dialog open={showKeyDialog} onOpenChange={setShowKeyDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Your New API Key</DialogTitle>
            <DialogDescription>
              Make sure to copy this key now. You won't be able to see it again!
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col sm:flex-row items-center gap-2 py-4">
            <div className="w-full">
              <div className="font-mono text-sm bg-muted p-3 rounded-md break-all">
                {newlyCreatedKey}
              </div>
            </div>
            <Button 
              size="icon" 
              variant="outline" 
              onClick={copyApiKeyToClipboard}
              className="shrink-0 w-full sm:w-auto mt-2 sm:mt-0"
            >
              <Copy className="h-4 w-4" />
              <span className="sr-only">Copy API key</span>
            </Button>
          </div>
          <DialogFooter>
            <Button 
              onClick={() => setShowKeyDialog(false)}
              className="bg-pink-600 hover:bg-pink-700 text-white w-full sm:w-auto"
            >
              I've Saved My API Key
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
} 