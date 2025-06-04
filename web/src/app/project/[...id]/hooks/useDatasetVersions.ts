import { useState, useEffect } from 'react'

export function useDatasetVersions(
  initialProject: any,
  inputLatestGenerationJobStatus: any
) {
  const [datasetVersions, setDatasetVersions] = useState<string[]>([])
  const [selectedVersion, setSelectedVersion] = useState<string>('')

  useEffect(() => {
    const fetchDatasetVersions = async () => {
      let latestVersion = initialProject?.latestDatasetVersion;
      const isLatestVersionNull = latestVersion == null || latestVersion == undefined;
      if (isLatestVersionNull) {
        latestVersion = 0;
      }
      const versions = Array.from({ length: latestVersion!! + 1 }, (_, i) => `V${i}`);
      
      if (inputLatestGenerationJobStatus.status == 'RUNNING' && !isLatestVersionNull) {
        versions.push(`V${latestVersion!! + 1}`);
      }

      setDatasetVersions(versions);
      if (versions.length > 0) {
        setSelectedVersion(versions[versions.length - 1]);
      }
    };
    fetchDatasetVersions()
  }, [initialProject, inputLatestGenerationJobStatus])

  return { datasetVersions, selectedVersion, setSelectedVersion, setDatasetVersions }
} 