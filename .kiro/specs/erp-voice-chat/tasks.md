# Implementation Plan

- [x] 1. Set up project structure and dependencies





  - Create Flask backend directory structure (api, services, models, repositories)
  - Set up pyproject.toml with Flask, Supabase, LiveKit Agents, Whisper, Piper TTS, and testing dependencies
  - Install Ollama locally and pull Llama 3 model
  - Configure environment variables for Supabase, LiveKit, Ollama, Whisper, Piper, and Spanish language settings
  - Create .env.example with all required configuration keys including free model settings
  - _Requirements: 8.1, 8.2, 8.3_

- [x] 2. Implement database schema and data access layer





  - Create Supabase migration files for ERP tables (customers, products, orders, order_items)
  - Create Supabase migration files for data quality tables (duplicate_groups, inconsistencies)
  - Implement SupabaseRepository class with CRUD operations
  - Create Python data models (DuplicateGroup, Inconsistency, ERPRecord)
  - _Requirements: 8.3, 6.2_

- [ ]* 2.1 Write property test for data access layer
  - **Property 5: Duplicate persistence**
  - **Validates: Requirements 2.3**

- [x] 3. Implement duplicate detection engine








  - Create DuplicateDetectionEngine class with detect_duplicates method
  - Implement similarity calculation using Levenshtein distance for text fields
  - Implement phone number normalization and comparison
  - Implement email comparison logic
  - Store detected duplicate groups in database
  - _Requirements: 2.1, 2.2, 2.3_

- [ ]* 3.1 Write property test for similarity score bounds
  - **Property 4: Similarity score bounds**
  - **Validates: Requirements 2.2**

- [ ]* 3.2 Write property test for duplicate detection accuracy
  - **Property 3: Duplicate detection accuracy**
  - **Validates: Requirements 2.1**

- [x] 4. Implement merge operation functionality




  - Create merge_duplicates method in DuplicateDetectionEngine
  - Implement logic to preserve all non-null values from both records
  - Implement conflict detection for fields with different non-null values
  - Implement foreign key reference updates after merge
  - Delete duplicate record after successful merge
  - _Requirements: 3.2, 3.3, 3.4, 3.5_

- [x] 4.1 Write property test for merge data preservation






  - **Property 7: Merge data preservation**
  - **Validates: Requirements 3.3**

- [ ]* 4.2 Write property test for merge referential integrity
  - **Property 8: Merge referential integrity**
  - **Validates: Requirements 3.4**

- [x] 5. Implement inconsistency analyzer





  - Create InconsistencyAnalyzer class with detect_inconsistencies method
  - Implement check_referential_integrity for foreign key validation
  - Implement check_calculations for computed totals validation
  - Implement check_formats for data format validation
  - Implement check_business_rules for business constraint validation
  - Store detected inconsistencies in database with categorization
  - _Requirements: 4.1, 4.2, 4.5_

- [ ]* 5.1 Write property test for inconsistency detection
  - **Property 10: Inconsistency detection completeness**
  - **Validates: Requirements 4.1**

- [ ]* 5.2 Write property test for inconsistency categorization
  - **Property 11: Inconsistency categorization**
  - **Validates: Requirements 4.2**

- [ ]* 5.3 Write property test for calculation inconsistency detection
  - **Property 13: Calculation inconsistency detection**
  - **Validates: Requirements 4.5**

- [x] 6. Implement inconsistency fix functionality





  - Create fix_inconsistency method in InconsistencyAnalyzer
  - Implement correction application with validation
  - Implement dependent data updates for referential integrity
  - Verify inconsistency is resolved after correction
  - _Requirements: 5.2, 5.5, 5.4_

- [ ]* 6.1 Write property test for correction verification
  - **Property 14: Correction verification**
  - **Validates: Requirements 5.4**

- [ ]* 6.2 Write property test for correction referential integrity
  - **Property 15: Correction referential integrity**
  - **Validates: Requirements 5.5**

- [x] 7. Checkpoint - Ensure all tests pass





  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Implement Flask REST API endpoints (local prototype - no authentication)





  - Create Flask app with CORS and error handling middleware
  - Implement GET /api/erp/query endpoint for ERP data queries
  - Implement POST /api/duplicates/detect endpoint
  - Implement GET /api/duplicates and GET /api/duplicates/{id} endpoints
  - Implement POST /api/duplicates/{id}/merge endpoint
  - Implement POST /api/inconsistencies/detect endpoint
  - Implement GET /api/inconsistencies and GET /api/inconsistencies/{id} endpoints
  - Implement POST /api/inconsistencies/{id}/fix endpoint
  - _Requirements: 6.2, 6.3, 6.4, 6.5_

- [ ]* 8.1 Write property test for data modification validation
  - **Property 17: Data modification validation**
  - **Validates: Requirements 6.5**

- [ ]* 8.2 Write unit tests for Flask API endpoints
  - Test query endpoint with various filters
  - Test duplicate detection and merge endpoints
  - Test inconsistency detection and fix endpoints

- [x] 9. Implement error handling and validation





  - Create standardized error response format
  - Implement validation for all API request bodies
  - Add error handling for database connection failures
  - Add error handling for constraint violations
  - Implement transaction rollback on errors
  - _Requirements: 7.3, 6.5_

- [ ]* 9.1 Write property test for error explanation
  - **Property 18: Error explanation**
  - **Validates: Requirements 7.3**

- [x] 10. Implement LiveKit voice agent with Spanish language support using free models




  - Create ERPVoiceAgent class extending LiveKit Agent
  - Configure Whisper STT (free, local) with Spanish language (es) support
  - Configure Piper TTS (free, open-source) with Spanish voice model
  - Configure Ollama with Llama 3 (free, local) for LLM
  - Implement handle_voice_session method for WebRTC connection
  - Set up agent instructions in Spanish for ERP administrator assistance
  - _Requirements: 1.1, 1.2, 1.4_

- [x] 11. Implement voice agent tools for ERP queries in Spanish





  - Create query_erp_data tool function with Spanish descriptions
  - Implement HTTP client for Flask API calls
  - Add error handling for API failures with Spanish error messages
  - Implement natural language response formatting in Spanish
  - _Requirements: 1.2, 1.3, 1.4_

- [ ]* 11.1 Write property test for voice query processing
  - **Property 1: Voice query processing completeness**
  - **Validates: Requirements 1.2, 1.3, 1.4**

- [x] 12. Implement voice agent tools for duplicate management in Spanish





  - Create detect_duplicates tool function with Spanish descriptions
  - Create get_duplicate_details tool function with Spanish output
  - Create merge_duplicates tool function with conflict resolution in Spanish
  - Implement conversational flow for merge confirmation in Spanish
  - _Requirements: 2.4, 2.5, 3.1, 3.5_

- [ ]* 12.1 Write property test for duplicate reporting
  - **Property 6: Duplicate reporting completeness**
  - **Validates: Requirements 2.4, 2.5**

- [ ]* 12.2 Write property test for merge conflict handling
  - **Property 9: Merge conflict handling**
  - **Validates: Requirements 3.5**

- [x] 13. Implement voice agent tools for inconsistency management in Spanish





  - Create detect_inconsistencies tool function with Spanish descriptions
  - Create get_inconsistency_details tool function with Spanish output
  - Create fix_inconsistency tool function with correction options in Spanish
  - Implement conversational flow for correction confirmation in Spanish
  - _Requirements: 4.3, 4.4, 5.1, 5.3_

- [ ]* 13.1 Write property test for inconsistency reporting
  - **Property 12: Inconsistency reporting completeness**
  - **Validates: Requirements 4.3, 4.4**

- [x] 14. Implement conversation context management in Spanish





  - Add conversation state tracking in voice agent
  - Implement context persistence across multiple queries in Spanish
  - Add entity reference resolution for Spanish (e.g., "ese cliente", "el primero")
  - _Requirements: 1.5_

- [ ]* 14.1 Write property test for context persistence
  - **Property 2: Conversation context persistence**
  - **Validates: Requirements 1.5**

- [x] 15. Implement voice error handling in Spanish





  - Add clarification requests in Spanish for unrecognized commands
  - Implement helpful responses in Spanish for empty query results
  - Add connection failure detection and reconnection logic with Spanish notifications
  - Implement ambiguous input handling with clarifying questions in Spanish
  - _Requirements: 7.1, 7.2, 7.4, 7.5_

- [x] 16. Create sample ERP data for testing





  - Create seed script for sample customers, products, orders
  - Include intentional duplicates for testing detection
  - Include intentional inconsistencies for testing analysis
  - Add script to reset database to initial state
  - _Requirements: 8.5_

- [ ]* 16.1 Write integration tests for end-to-end workflows
  - Test complete duplicate detection and merge workflow via API
  - Test complete inconsistency detection and fix workflow via API

- [x] 17. Final checkpoint - Ensure all tests pass





  - Ensure all tests pass, ask the user if questions arise.

- [ ] 18. Create deployment configuration
  - Create Dockerfile for Flask backend
  - Update existing Dockerfile for LiveKit agent
  - Create docker-compose.yml for local development
  - Document environment variables in README
  - Add deployment instructions for LiveKit Cloud
  - _Requirements: 8.1, 8.2_

- [ ] 19. Create documentation in Spanish
  - Write README with setup instructions in Spanish
  - Document API endpoints with example requests/responses in Spanish
  - Document voice commands and conversation flows in Spanish
  - Add troubleshooting guide for common issues in Spanish
  - _Requirements: 8.5_
