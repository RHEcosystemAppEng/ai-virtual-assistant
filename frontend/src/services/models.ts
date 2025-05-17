import { AI_MODELS_API_ENDPOINT } from '@/config/api';
import { Model } from '@/types';

export const fetchModels = async (): Promise<Model[]> => {
  const response = await fetch(AI_MODELS_API_ENDPOINT);
  if (!response.ok) {
    throw new Error('Network response was not ok');
  }
  return response.json();
};
