#!/bin/bash

# Script to add environment variables to Vercel
# Run this from the student-os-rag directory

echo "Adding environment variables to Vercel..."

vercel env add OPENAI_API_KEY production
vercel env add API_KEY production
vercel env add EMBEDDING_MODEL production
vercel env add EMBEDDING_DIMENSIONS production
vercel env add MAX_CHUNK_TOKENS production
vercel env add CHUNK_OVERLAP_TOKENS production
vercel env add RATE_LIMIT production

echo "Environment variables added! Now redeploy:"
echo "vercel --prod"
